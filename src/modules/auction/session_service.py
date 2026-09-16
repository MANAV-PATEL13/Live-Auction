from datetime import datetime, timezone

from beanie import PydanticObjectId

from src.core.security import hash_password
from src.modules.auction.constants import (
    AuctionSessionStatus,
    AuctionSortDirection,
    AuctionSortField,
    AuctionStatus,
)
from src.modules.auction.currency import maroon_to_pushp
from src.modules.auction.model import Auction
from src.modules.auction.redis_service import auction_redis
from src.modules.auction.schema import QuickAddPlayerRequest
from src.modules.auction.session_model import AuctionSession
from src.modules.auction.session_repository import AuctionSessionRepository
from src.modules.registration.model import Registration
from src.modules.users.model import User
from src.common.websocket.websocket import auction_websocket, AuctionWebSocketEvent
from src.modules.auction.activity_log_service import auction_activity_service


class AuctionSessionService:

    def __init__(self):
        self.repository = AuctionSessionRepository()

    # =========================================================
    # START AUCTION
    # =========================================================

    async def start(
        self,
        sort_by: str = AuctionSortField.BASE_PRICE,
        sort_direction: str = AuctionSortDirection.ASC,
    ) -> AuctionSession:

        # -----------------------------------------------------
        # 1. Check existing session
        # -----------------------------------------------------

        current = await self.repository.get_current()

        if current:
            raise ValueError(
                "An auction session is already running"
            )

        # -----------------------------------------------------
        # 2. Get eligible players
        # -----------------------------------------------------

        users = await User.find(
            User.is_registered == True,
            User.is_active == True,
            User.team_id == None,
        ).to_list()

        if not users:
            raise ValueError(
                "No eligible registered players found"
            )

        # -----------------------------------------------------
        # 3. Sort players
        # -----------------------------------------------------

        users = self._sort_users(
            users,
            sort_by,
            sort_direction,
        )

        user_ids = [
            user.id
            for user in users
        ]

        # -----------------------------------------------------
        # 4. Create session
        # -----------------------------------------------------

        now = datetime.now(timezone.utc)

        session = AuctionSession(
            status=AuctionSessionStatus.LIVE,
            sort_by=sort_by,
            sort_direction=sort_direction,
            remaining_queue=user_ids,
            unsold_queue=[],
            current_user_id=None,
            current_auction_id=None,
            started_at=now,
        )

        await self.repository.create(session)

        # -----------------------------------------------------
        # 5. Reset Redis live state
        # -----------------------------------------------------

        await auction_redis.clear_live_state()

        await auction_redis.set_session_id(
            str(session.id)
        )

        await auction_redis.set_status(
            AuctionSessionStatus.LIVE
        )

        await auction_redis.set_remaining_queue(
            [
                str(user_id)
                for user_id in user_ids
            ]
        )

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.SESSION_STARTED,
            {
                "session_id": str(session.id),
                "status": session.status,
                "remaining_count": len(session.remaining_queue),
            },
        )

        # Log session start
        await auction_activity_service.log_activity(
            type="SESSION_STATUS",
            title="Auction Session Started",
            description=f"Continuous auction session started ({len(session.remaining_queue)} students in queue)",
            session_id=session.id,
            metadata={"remaining_count": len(session.remaining_queue), "status": session.status},
        )

        return session

        # =========================================================
        # SORT PLAYERS
        # =========================================================

    @staticmethod
    def _sort_users(
        users: list[User],
        sort_by: str,
        sort_direction: str,
    ) -> list[User]:

        reverse = (
            sort_direction
            == AuctionSortDirection.DESC
        )

        if sort_by in [AuctionSortField.CURRENT_QUEUE, "current", "default"]:
            return list(reversed(users)) if reverse else users

        if sort_by == AuctionSortField.CREATED_AT:
            return sorted(
                users,
                key=lambda user: user.created_at or datetime.min,
                reverse=reverse,
            )

        if sort_by == AuctionSortField.BASE_PRICE:

            return sorted(
                users,
                key=lambda user: user.base_price,
                reverse=reverse,
            )

        if sort_by == AuctionSortField.NAME:

            return sorted(
                users,
                key=lambda user: (
                    user.name or ""
                ).casefold(),
                reverse=reverse,
            )

        if sort_by == AuctionSortField.ROLL_NO:

            return sorted(
                users,
                key=AuctionSessionService._roll_no_sort_key,
                reverse=reverse,
            )

        # Fallback to existing order if unknown
        return list(reversed(users)) if reverse else users

    # =========================================================
    # ROLL NO SORT
    # =========================================================

    @staticmethod
    def _roll_no_sort_key(
        user: User,
    ):

        roll_no = user.roll_no

        if not roll_no:
            return (1, "")

        if roll_no.isdigit():
            return (0, int(roll_no))

        return (0, roll_no.casefold())

    # =========================================================
    # GET NEXT PLAYER
    # =========================================================

    # =========================================================
# GET NEXT PLAYER
# =========================================================

    async def get_next_player(
        self,
        session: AuctionSession,
    ) -> Auction | None:

        # ======================================================
        # 1. Session must be active (auto-resume if PAUSED)
        # ======================================================

        if session.status == AuctionSessionStatus.PAUSED:
            session.status = AuctionSessionStatus.LIVE
            await self.repository.update(session)
            await auction_redis.set_status(AuctionSessionStatus.LIVE)
            await auction_websocket.broadcast(
                AuctionWebSocketEvent.RESUMED,
                {"session_id": str(session.id), "status": "LIVE"},
            )
        elif session.status != AuctionSessionStatus.LIVE:
            raise ValueError(
                "Auction session is not live. Please start or launch an auction session."
            )

        # ======================================================
        # 2. Do not move to next player while current auction
        #    is still active
        # ======================================================

        if session.current_auction_id:

            current_auction = await Auction.get(
                session.current_auction_id
            )

            if (
                current_auction
                and current_auction.status == AuctionStatus.LIVE
            ):
                # Automatically close previous active auction as UNSOLD and move to unsold queue
                current_auction.status = AuctionStatus.UNSOLD
                current_auction.ended_at = datetime.now(timezone.utc)
                await current_auction.save()

                if current_auction.user_id not in session.unsold_queue:
                    session.unsold_queue.append(current_auction.user_id)
                await auction_redis.push_unsold_player(str(current_auction.user_id))

            # --------------------------------------------------
            # Stale current pointers
            # --------------------------------------------------

            session.current_user_id = None
            session.current_auction_id = None

            await self.repository.update(session)

        # ======================================================
        # 3. Peek next player
        #
        # IMPORTANT:
        # Do NOT pop before MongoDB auction creation.
        # ======================================================

        user_id = await auction_redis.peek_next_player()

        # ======================================================
        # 4. Remaining queue empty
        #    → move UNSOLD players into next pass
        # ======================================================

        if user_id is None:

            unsold_ids = await auction_redis.get_unsold_queue()

            # --------------------------------------------------
            # No remaining + no unsold
            #
            # Auction stays LIVE.
            # Admin can call NEXT again after players become
            # eligible, or explicitly END the session.
            # --------------------------------------------------

            if not unsold_ids:

                session.current_user_id = None
                session.current_auction_id = None

                await self.repository.update(session)

                await auction_redis.clear_current_auction()

                return None

            # --------------------------------------------------
            # Start another pass
            # --------------------------------------------------

            await auction_redis.set_remaining_queue(
                unsold_ids
            )

            await auction_redis.set_unsold_queue([])

            session.remaining_queue = [
                PydanticObjectId(user_id)
                for user_id in unsold_ids
            ]

            session.unsold_queue = []

            await self.repository.update(session)

            # --------------------------------------------------
            # Peek first player of new pass
            # --------------------------------------------------

            user_id = await auction_redis.peek_next_player()

        # ======================================================
        # 5. Validate player ID
        # ======================================================

        if not user_id:
            raise ValueError(
                "Unable to determine next player"
            )

        if not PydanticObjectId.is_valid(user_id):
            raise ValueError(
                "Invalid player ID in auction queue"
            )

        player_id = PydanticObjectId(user_id)

        # ======================================================
        # 6. Get player
        # ======================================================

        user = await User.get(player_id)

        if not user:
            raise ValueError(
                "Player not found"
            )

        if not user.is_registered:
            raise ValueError(
                "Player is not registered"
            )

        if not user.is_active:
            raise ValueError(
                "Player is not active"
            )

        if user.team_id is not None:
            raise ValueError(
                "Player is already assigned to a team"
            )

        # ======================================================
        # 7. Create auction attempt
        # ======================================================

        now = datetime.now(timezone.utc)

        auction = Auction(
            session_id=session.id,
            user_id=user.id,
            base_price=user.base_price,
            status=AuctionStatus.LIVE,
            current_bid=user.base_price,
            current_team_id=None,
            started_at=now,
        )

        # ------------------------------------------------------
        # IMPORTANT:
        # This is an Auction document, so insert it directly.
        # Do NOT use AuctionSessionRepository.create().
        # ------------------------------------------------------

        await auction.insert()

        # ======================================================
        # 8. Remove player from Mongo remaining queue
        # ======================================================

        if player_id in session.remaining_queue:
            session.remaining_queue.remove(player_id)

        session.current_user_id = user.id
        session.current_auction_id = auction.id

        await self.repository.update(session)

        # ======================================================
        # 9. NOW remove player from Redis queue
        #
        # We intentionally waited until MongoDB was updated.
        # ======================================================

        popped_user_id = await auction_redis.pop_next_player()

        if popped_user_id != user_id:
            raise ValueError(
                "Auction queue changed unexpectedly"
            )

        # ======================================================
        # 10. Update Redis current auction (immediately LIVE on floor)
        # ======================================================

        await auction_redis.set_current_auction(
            {
                "auction_id": str(auction.id),
                "session_id": str(session.id),
                "user_id": str(user.id),
                "base_price": user.base_price,
                "current_bid": user.base_price,
                "current_team_id": None,
                "status": "LIVE",
            }
        )

        await auction_redis.set_status("LIVE")

        # ======================================================
        # 11. Initial bid state
        # ======================================================

        await auction_redis.set_bid(
            user.base_price,
            "",
        )

        # Fetch sports data for player start broadcast
        sports_data = None
        from src.modules.registration.model import Registration
        reg = await Registration.find_one(Registration.user_id == user.id)
        if reg:
            sports_data = reg.sports_map

        player_dict = {
            "id": str(user.id),
            "name": user.name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "roll_no": user.roll_no,
            "image_url": user.image_url,
            "base_price": user.base_price,
            "sports": sports_data,
            "games": reg.games if reg else [],
            "experience_years": reg.experience_years if reg else None,
            "critical_situation": reg.critical_situation if reg else [],
            "creative_talent": reg.creative_talent if reg else [],
            "sportsmanship": reg.sportsmanship if reg else [],
            "preference": reg.preference if reg else [],
            "questions": {
                "games": reg.games if reg else [],
                "experience_years": reg.experience_years if reg else None,
                "critical_situation": reg.critical_situation if reg else [],
                "creative_talent": reg.creative_talent if reg else [],
                "sportsmanship": reg.sportsmanship if reg else [],
                "preference": reg.preference if reg else [],
            } if reg else None,
        }

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.PLAYER_STARTED,
            {
                "auction_id": str(auction.id),
                "session_id": str(session.id),
                "user_id": str(user.id),
                "player": player_dict,
                "name": user.name,
                "roll_no": user.roll_no,
                "image_url": user.image_url,
                "base_price": user.base_price,
                "current_bid": user.base_price,
                "status": "LIVE",
                "is_staged": False,
            },
        )

        # Log player staged on floor
        clean_name = f"{user.roll_no} - {user.name}" if user.roll_no else user.name
        await auction_activity_service.log_activity(
            type="PLAYER_START",
            title="Player on Floor",
            description=f"{clean_name} entered the floor (Base: {user.base_price} M)",
            session_id=session.id,
            auction_id=auction.id,
            metadata={"player_id": str(user.id), "player_name": user.name, "roll_no": user.roll_no, "base_price": user.base_price},
        )

        return auction

    async def recover(self) -> AuctionSession | None:

        # --------------------------------------------------
        # 1. MongoDB is the source of truth
        # --------------------------------------------------

        session = await self.repository.get_current()

        if not session:
            await auction_redis.clear_live_state()
            return None

        # --------------------------------------------------
        # 2. Clear existing Redis state
        # --------------------------------------------------

        await auction_redis.clear_live_state()

        await auction_redis.set_session_id(
            str(session.id)
        )

        await auction_redis.set_status(
            session.status
        )

        # --------------------------------------------------
        # 3. Restore remaining queue
        # --------------------------------------------------

        await auction_redis.set_remaining_queue(
            [
                str(user_id)
                for user_id in session.remaining_queue
            ]
        )

        # --------------------------------------------------
        # 4. Restore UNSOLD queue
        # --------------------------------------------------

        await auction_redis.set_unsold_queue(
            [
                str(user_id)
                for user_id in session.unsold_queue
            ]
        )

        # --------------------------------------------------
        # 5. Restore current auction
        # --------------------------------------------------

        if session.current_auction_id:

            auction = await Auction.get(
                session.current_auction_id
            )

            if auction and auction.status == AuctionStatus.LIVE:

                await auction_redis.set_current_auction(
                    {
                        "auction_id": str(auction.id),
                        "session_id": str(session.id),
                        "user_id": str(auction.user_id),
                        "base_price": auction.base_price,
                        "current_bid": auction.current_bid,
                        "current_team_id": (
                            str(auction.current_team_id)
                            if auction.current_team_id
                            else None
                        ),
                        "status": auction.status,
                    }
                )

                await auction_redis.set_bid(
                    auction.current_bid,
                    (
                        str(auction.current_team_id)
                        if auction.current_team_id
                        else ""
                    ),
                )

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.RESUMED,
            {
                "session_id": str(session.id),
                "status": session.status,
            },
        )

        return session

    async def pause(
        self,
        session_id: PydanticObjectId,
    ) -> AuctionSession:

        session = await self.repository.get_by_id(session_id)

        if not session:
            raise ValueError("Auction session not found")

        if session.status != AuctionSessionStatus.LIVE:
            raise ValueError("Auction session is not live")

        session.status = AuctionSessionStatus.PAUSED
        session.paused_at = datetime.now(timezone.utc)

        await self.repository.update(session)

        await auction_redis.set_status(
            AuctionSessionStatus.PAUSED
        )

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.PAUSED,
            {
                "session_id": str(session.id),
                "status": session.status,
            },
        )

        # Log session paused
        await auction_activity_service.log_activity(
            type="SESSION_STATUS",
            title="Auction Paused ⏸️",
            description="Auction session paused by floor auctioneer",
            session_id=session.id,
            metadata={"status": "PAUSED"},
        )

        return session


    async def resume(
        self,
        session_id: PydanticObjectId,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> AuctionSession:

        session = await self.repository.get_by_id(session_id)

        if not session:
            raise ValueError("Auction session not found")

        if session.status != AuctionSessionStatus.PAUSED:
            raise ValueError(
                "Auction session is not paused"
            )

        # --------------------------------------------------
        # Apply new sorting if supplied
        # --------------------------------------------------

        if sort_by is not None:
            session.sort_by = sort_by

        if sort_direction is not None:
            session.sort_direction = sort_direction

        # --------------------------------------------------
        # Get remaining players
        #
        # Current player is NOT included.
        # --------------------------------------------------

        remaining_ids = session.remaining_queue

        users = []

        for user_id in remaining_ids:

            user = await User.get(user_id)

            if not user:
                continue

            if not user.is_registered:
                continue

            if not user.is_active:
                continue

            if user.team_id is not None:
                continue

            users.append(user)

        # --------------------------------------------------
        # Re-sort remaining players
        # --------------------------------------------------

        users = self._sort_users(
            users,
            session.sort_by,
            session.sort_direction,
        )

        session.remaining_queue = [
            user.id
            for user in users
        ]

        session.status = AuctionSessionStatus.LIVE

        await self.repository.update(session)

        # --------------------------------------------------
        # Rebuild Redis
        # --------------------------------------------------

        await auction_redis.set_session_id(
            str(session.id)
        )

        await auction_redis.set_status(
            AuctionSessionStatus.LIVE
        )

        await auction_redis.set_remaining_queue(
            [
                str(user_id)
                for user_id in session.remaining_queue
            ]
        )

        # --------------------------------------------------
        # Preserve current auction if one exists
        # --------------------------------------------------

        if session.current_auction_id:

            auction = await Auction.get(
                session.current_auction_id
            )

            if auction and auction.status == AuctionStatus.LIVE:

                await auction_redis.set_current_auction(
                    {
                        "auction_id": str(auction.id),
                        "session_id": str(session.id),
                        "user_id": str(auction.user_id),
                        "base_price": auction.base_price,
                        "current_bid": auction.current_bid,
                        "current_team_id": (
                            str(auction.current_team_id)
                            if auction.current_team_id
                            else None
                        ),
                        "status": AuctionStatus.LIVE,
                    }
                )

                await auction_redis.set_bid(
                    auction.current_bid,
                    (
                        str(auction.current_team_id)
                        if auction.current_team_id
                        else ""
                    ),
                )

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.RESUMED,
            {
                "session_id": str(session.id),
                "status": session.status,
            },
        )

        # Log session resumed
        await auction_activity_service.log_activity(
            type="SESSION_STATUS",
            title="Auction Resumed ▶️",
            description="Auction session resumed by floor auctioneer",
            session_id=session.id,
            metadata={"status": "LIVE"},
        )

        return session


    async def end(
        self,
        session_id: PydanticObjectId,
    ) -> AuctionSession:

        session = await self.repository.get_by_id(session_id)

        if not session:
            raise ValueError(
                "Auction session not found"
            )

        if session.status not in (
            AuctionSessionStatus.LIVE,
            AuctionSessionStatus.PAUSED,
        ):
            raise ValueError(
                "Auction session is already ended"
            )

        # --------------------------------------------------
        # Do not allow ending while a player is actively
        # being auctioned.
        # --------------------------------------------------

        if session.current_auction_id:

            auction = await Auction.get(
                session.current_auction_id
            )

            if auction and auction.status == AuctionStatus.LIVE:

                raise ValueError(
                    "Cannot end auction while a player auction is active"
                )

        # --------------------------------------------------
        # End session
        # --------------------------------------------------

        session.status = AuctionSessionStatus.ENDED
        session.ended_at = datetime.now(timezone.utc)

        session.current_user_id = None
        session.current_auction_id = None

        await self.repository.update(session)

        # --------------------------------------------------
        # Clear Redis live state
        # --------------------------------------------------

        await auction_redis.clear_live_state()

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.ENDED,
            {
                "session_id": str(session.id),
                "status": session.status,
            },
        )

        # Log session ended
        await auction_activity_service.log_activity(
            type="SESSION_STATUS",
            title="Auction Concluded 🛑",
            description="Continuous auction session concluded and squad rosters finalized",
            session_id=session.id,
            metadata={"status": "ENDED"},
        )

        return session

    # =========================================================
    # GET UPCOMING PLAYERS IN QUEUE
    # =========================================================

    async def get_upcoming_players(
        self,
        limit: int = 2,
    ) -> list[dict]:
        session = await self.repository.get_current()
        if not session:
            return []

        remaining_ids = await auction_redis.get_remaining_queue()
        if not remaining_ids:
            remaining_ids = [str(uid) for uid in session.remaining_queue]

        if not remaining_ids:
            unsold_ids = await auction_redis.get_unsold_queue()
            if not unsold_ids:
                unsold_ids = [str(uid) for uid in session.unsold_queue]
            remaining_ids = unsold_ids

        target_ids = remaining_ids[:limit]
        result: list[dict] = []

        from src.modules.registration.model import Registration
        from src.modules.auction.currency import maroon_to_pushp

        for uid_str in target_ids:
            if not PydanticObjectId.is_valid(uid_str):
                continue
            user = await User.get(PydanticObjectId(uid_str))
            if not user:
                continue

            sports_data = None
            reg = await Registration.find_one(Registration.user_id == user.id)
            if reg:
                sports_data = reg.sports_map

            result.append(
                {
                    "id": str(user.id),
                    "name": user.name,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "roll_no": user.roll_no,
                    "image_url": user.image_url,
                    "base_price": user.base_price,
                    "base_price_display": maroon_to_pushp(user.base_price),
                    "sports": sports_data,
                    "games": reg.games if reg else [],
                    "experience_years": reg.experience_years if reg else None,
                    "critical_situation": reg.critical_situation if reg else [],
                    "creative_talent": reg.creative_talent if reg else [],
                    "sportsmanship": reg.sportsmanship if reg else [],
                    "preference": reg.preference if reg else [],
                    "questions": {
                        "games": reg.games if reg else [],
                        "experience_years": reg.experience_years if reg else None,
                        "critical_situation": reg.critical_situation if reg else [],
                        "creative_talent": reg.creative_talent if reg else [],
                        "sportsmanship": reg.sportsmanship if reg else [],
                        "preference": reg.preference if reg else [],
                    } if reg else None,
                }
            )

        return result

    # =========================================================
    # GET FULL QUEUE (DETAILED CARDS)
    # =========================================================

    async def get_full_queue(self) -> dict:
        session = await self.repository.get_current()
        if not session:
            return {"remaining": [], "unsold": [], "current_player": None, "session_status": "PENDING"}

        remaining_ids = await auction_redis.get_remaining_queue()
        if not remaining_ids:
            remaining_ids = [str(uid) for uid in session.remaining_queue]

        unsold_ids = await auction_redis.get_unsold_queue()
        if not unsold_ids:
            unsold_ids = [str(uid) for uid in session.unsold_queue]

        from src.modules.registration.model import Registration
        from src.modules.auction.currency import maroon_to_pushp

        async def fetch_player_cards(id_list: list[str]) -> list[dict]:
            cards = []
            for uid_str in id_list:
                if not PydanticObjectId.is_valid(uid_str):
                    continue
                user = await User.get(PydanticObjectId(uid_str))
                if not user:
                    continue
                sports_data = None
                reg = await Registration.find_one(Registration.user_id == user.id)
                if reg:
                    sports_data = reg.sports_map
                cards.append({
                    "id": str(user.id),
                    "name": user.name,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "roll_no": user.roll_no,
                    "image_url": user.image_url,
                    "base_price": user.base_price,
                    "base_price_display": maroon_to_pushp(user.base_price),
                    "sports": sports_data,
                    "is_registered": user.is_registered,
                })
            return cards

        remaining_cards = await fetch_player_cards(remaining_ids)
        unsold_cards = await fetch_player_cards(unsold_ids)

        return {
            "session_id": str(session.id),
            "session_status": session.status,
            "remaining": remaining_cards,
            "unsold": unsold_cards,
            "remaining_count": len(remaining_cards),
            "unsold_count": len(unsold_cards),
        }

    # =========================================================
    # REORDER QUEUE
    # =========================================================

    async def reorder_queue(self, user_ids: list[str]) -> dict:
        session = await self.repository.get_current()
        if not session:
            raise ValueError("No active auction session found to reorder")

        valid_object_ids = []
        for uid_str in user_ids:
            if PydanticObjectId.is_valid(uid_str):
                valid_object_ids.append(PydanticObjectId(uid_str))

        if not valid_object_ids:
            raise ValueError("No valid user IDs provided for reordering")

        session.remaining_queue = valid_object_ids
        await self.repository.update(session)

        # Sync with Redis
        await auction_redis.set_remaining_queue([str(uid) for uid in valid_object_ids])

        # WebSocket Broadcast
        await auction_websocket.broadcast(
            AuctionWebSocketEvent.SESSION_STARTED,
            {
                "session_id": str(session.id),
                "status": session.status,
                "remaining_count": len(session.remaining_queue),
            },
        )

        await auction_activity_service.log_activity(
            type="QUEUE_UPDATED",
            title="Auction Queue Reordered 🔀",
            description=f"Admin rearranged remaining queue ({len(session.remaining_queue)} students)",
            session_id=session.id,
            metadata={"queue_count": len(session.remaining_queue)},
        )

        return {
            "session_id": str(session.id),
            "remaining_count": len(session.remaining_queue),
            "message": "Queue reordered successfully",
        }

    # =========================================================
    # REMOVE PLAYER FROM QUEUE
    # =========================================================

    async def remove_from_queue(self, user_id: str) -> dict:
        session = await self.repository.get_current()
        if not session:
            raise ValueError("No active auction session found")

        if not PydanticObjectId.is_valid(user_id):
            raise ValueError("Invalid user ID")

        target_obj_id = PydanticObjectId(user_id)
        removed = False
        if target_obj_id in session.remaining_queue:
            session.remaining_queue.remove(target_obj_id)
            removed = True
        if target_obj_id in session.unsold_queue:
            session.unsold_queue.remove(target_obj_id)
            removed = True

        if not removed:
            raise ValueError("Player not found in remaining or unsold queue")

        await self.repository.update(session)
        await auction_redis.set_remaining_queue([str(uid) for uid in session.remaining_queue])
        await auction_redis.set_unsold_queue([str(uid) for uid in session.unsold_queue])

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.SESSION_STARTED,
            {
                "session_id": str(session.id),
                "status": session.status,
                "remaining_count": len(session.remaining_queue),
            },
        )

        return {
            "session_id": str(session.id),
            "remaining_count": len(session.remaining_queue),
            "message": "Player removed from queue",
        }

    # =========================================================
    # RE-QUEUE UNSOLD PLAYERS
    # =========================================================

    async def requeue_unsold(self, user_id: str | None = None) -> dict:
        session = await self.repository.get_current()
        if not session:
            raise ValueError("No active auction session found")

        if user_id:
            if not PydanticObjectId.is_valid(user_id):
                raise ValueError("Invalid user ID")
            target_obj_id = PydanticObjectId(user_id)
            if target_obj_id not in session.unsold_queue:
                raise ValueError("Player is not in unsold queue")
            session.unsold_queue.remove(target_obj_id)
            session.remaining_queue.append(target_obj_id)
        else:
            if not session.unsold_queue:
                raise ValueError("Unsold queue is currently empty")
            session.remaining_queue.extend(session.unsold_queue)
            session.unsold_queue = []

        await self.repository.update(session)
        await auction_redis.set_remaining_queue([str(uid) for uid in session.remaining_queue])
        await auction_redis.set_unsold_queue([str(uid) for uid in session.unsold_queue])

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.SESSION_STARTED,
            {
                "session_id": str(session.id),
                "status": session.status,
                "remaining_count": len(session.remaining_queue),
            },
        )

        await auction_activity_service.log_activity(
            type="QUEUE_UPDATED",
            title="Unsold Players Re-queued 🔄",
            description=f"Moved unsold player(s) back into active bidding queue",
            session_id=session.id,
            metadata={
                "remaining_count": len(session.remaining_queue),
                "unsold_count": len(session.unsold_queue),
            },
        )

        return {
            "session_id": str(session.id),
            "remaining_count": len(session.remaining_queue),
            "unsold_count": len(session.unsold_queue),
            "message": "Player(s) re-queued successfully",
        }

    async def import_queue_from_csv(
        self,
        file_content: bytes,
        auto_start: bool = False,
        append_mode: bool = False,
    ) -> dict:
        from src.common.csv_service import CSVService

        columns, rows = CSVService.read(file_content)

        # Detect roll_no column name
        roll_col = None
        for col in columns:
            clean_col = col.lower().replace(" ", "").replace("_", "").replace("-", "")
            if clean_col in ["rollno", "roll", "rollnumber", "studentid"]:
                roll_col = col
                break

        if not roll_col and columns:
            roll_col = columns[0]

        if not roll_col:
            raise ValueError("CSV file has no valid roll number column")

        seen_user_ids = set()
        matched_users: list[User] = []
        unmatched_roll_nos: list[str] = []
        already_assigned: list[dict] = []
        duplicates: list[str] = []

        for row in rows:
            raw_roll = row.get(roll_col)
            if not raw_roll:
                continue
            roll_str = str(raw_roll).strip()
            if not roll_str:
                continue

            users = await User.find(
                User.roll_no == roll_str,
            ).to_list()

            if not users:
                unmatched_roll_nos.append(roll_str)
                continue

            valid_user = None
            for u in users:
                if not u.is_registered or not u.is_active:
                    continue
                if u.team_id is not None:
                    already_assigned.append({"roll_no": u.roll_no, "name": u.name, "team_id": str(u.team_id)})
                    continue
                valid_user = u
                break

            if not valid_user:
                if not any(a["roll_no"] == roll_str for a in already_assigned):
                    unmatched_roll_nos.append(roll_str)
                continue

            if valid_user.id in seen_user_ids:
                duplicates.append(roll_str)
                continue

            seen_user_ids.add(valid_user.id)
            matched_users.append(valid_user)

        if not matched_users:
            raise ValueError(
                f"No eligible unassigned players found in the uploaded CSV. (Checked {len(rows)} rows)"
            )

        matched_user_ids = [u.id for u in matched_users]
        session = await self.repository.get_current()

        if session and session.status in [AuctionSessionStatus.LIVE, AuctionSessionStatus.PAUSED]:
            if append_mode:
                existing_set = set(session.remaining_queue) | set(session.unsold_queue)
                if session.current_user_id:
                    existing_set.add(session.current_user_id)
                new_additions = [uid for uid in matched_user_ids if uid not in existing_set]
                session.remaining_queue.extend(new_additions)
            else:
                session.remaining_queue = matched_user_ids

            session.sort_by = "custom_csv"
            await self.repository.update(session)

            await auction_redis.set_remaining_queue([str(uid) for uid in session.remaining_queue])

            await auction_websocket.broadcast(
                AuctionWebSocketEvent.SESSION_STARTED,
                {
                    "session_id": str(session.id),
                    "status": session.status,
                    "remaining_count": len(session.remaining_queue),
                },
            )

            await auction_activity_service.log_activity(
                type="QUEUE_UPDATED",
                title="Custom CSV Queue Applied 📋",
                description=f"Auction queue prepared with {len(session.remaining_queue)} students in CSV sequence",
                session_id=session.id,
                metadata={
                    "total_csv_rows": len(rows),
                    "matched_count": len(matched_users),
                    "queue_count": len(session.remaining_queue),
                },
            )

        elif auto_start or not session or session.status == AuctionSessionStatus.ENDED:
            now = datetime.now(timezone.utc)
            session = AuctionSession(
                status=AuctionSessionStatus.LIVE,
                sort_by="custom_csv",
                sort_direction=AuctionSortDirection.ASC,
                remaining_queue=matched_user_ids,
                unsold_queue=[],
                current_user_id=None,
                current_auction_id=None,
                started_at=now,
            )
            await self.repository.create(session)

            await auction_redis.clear_live_state()
            await auction_redis.set_session_id(str(session.id))
            await auction_redis.set_status(AuctionSessionStatus.LIVE)
            await auction_redis.set_remaining_queue([str(uid) for uid in matched_user_ids])

            await auction_websocket.broadcast(
                AuctionWebSocketEvent.SESSION_STARTED,
                {
                    "session_id": str(session.id),
                    "status": session.status,
                    "remaining_count": len(session.remaining_queue),
                },
            )

            await auction_activity_service.log_activity(
                type="SESSION_STATUS",
                title="Auction Started (CSV Queue) 🚀",
                description=f"Auction session started with custom CSV queue order ({len(matched_user_ids)} students)",
                session_id=session.id,
                metadata={"queue_count": len(matched_user_ids)},
            )

        return {
            "success": True,
            "total_rows": len(rows),
            "matched_count": len(matched_users),
            "unmatched_count": len(unmatched_roll_nos),
            "unmatched_roll_nos": unmatched_roll_nos[:50],
            "already_assigned_count": len(already_assigned),
            "already_assigned": already_assigned[:50],
            "duplicates_count": len(duplicates),
            "queue_count": len(session.remaining_queue) if session else len(matched_users),
            "session_id": str(session.id) if session else None,
            "session_status": session.status if session else None,
            "preview": [
                {
                    "id": str(u.id),
                    "name": u.name,
                    "roll_no": u.roll_no,
                    "base_price": u.base_price,
                }
                for u in matched_users[:15]
            ],
        }

    # =========================================================
    # QUICK ADD PLAYER (ON-THE-FLY REGISTRATION & QUEUE INJECTION)
    # =========================================================

    async def quick_add_player(
        self,
        data: QuickAddPlayerRequest,
        created_by: PydanticObjectId | None = None,
    ) -> dict:
        email = data.email.strip().lower() if data.email else ""
        roll_clean = (data.roll_no or "player").strip().lower().replace(" ", "").replace("#", "")
        if not email or "@" not in email or not email.endswith((".com", ".org", ".net", ".in", ".edu", ".io", ".co")):
            email = f"{roll_clean}@bhaktipurv.com"

        user = await User.find_one(User.email == email)
        first = data.first_name.strip()
        middle = data.middle_name.strip() if data.middle_name else ""
        last = data.last_name.strip()
        full_name = f"{first} {middle + ' ' if middle else ''}{last}".strip()

        if user:
            user.first_name = first
            user.middle_name = middle if middle else None
            user.last_name = last
            user.name = full_name
            if data.roll_no:
                user.roll_no = data.roll_no.strip()
            if data.mobile:
                user.mobile = data.mobile.strip()
            if data.image_url:
                user.image_url = data.image_url.strip()
            user.base_price = max(data.base_price, 0)
            user.is_registered = True
            user.is_active = True
            user.is_allowed = True
            user.updated_at = datetime.now(timezone.utc)
            await user.save()
        else:
            default_password = f"{(data.roll_no or 'bhakti').strip()}.@321"
            user = User(
                name=full_name,
                first_name=first,
                middle_name=middle if middle else None,
                last_name=last,
                roll_no=data.roll_no.strip() if data.roll_no else None,
                email=email,
                mobile=data.mobile.strip() if data.mobile else None,
                image_url=data.image_url.strip() if data.image_url else None,
                password_hash=hash_password(default_password),
                base_price=max(data.base_price, 0),
                is_registered=True,
                is_active=True,
                is_allowed=True,
                is_superuser=False,
                group_ids=[],
            )
            await user.save()

        # Update or create Registration document
        registration = await Registration.find_one(Registration.user_id == user.id)
        if registration:
            registration.games = data.games or []
            registration.experience_years = data.experience_years
            registration.critical_situation = data.critical_situation or []
            registration.creative_talent = data.creative_talent or []
            registration.sportsmanship = data.sportsmanship or []
            registration.preference = data.preference or []
            if created_by:
                registration.mark_updated(created_by)
            await registration.save()
        else:
            registration = Registration(
                user_id=user.id,
                games=data.games or [],
                experience_years=data.experience_years,
                critical_situation=data.critical_situation or [],
                creative_talent=data.creative_talent or [],
                sportsmanship=data.sportsmanship or [],
                preference=data.preference or [],
            )
            if created_by:
                registration.mark_created(created_by)
            await registration.save()

        # Queue injection if active session exists
        session = await self.repository.get_current()
        in_queue = False
        queue_pos = None
        remaining_count = 0

        if session and session.status in [AuctionSessionStatus.LIVE, AuctionSessionStatus.PAUSED, AuctionSessionStatus.PENDING]:
            # Check if user is already in queue or on stage
            if user.id == session.current_user_id:
                in_queue = True
                queue_pos = "CURRENT_ON_STAGE"
            elif user.id in session.unsold_queue:
                in_queue = True
                queue_pos = "UNSOLD_QUEUE"
            elif user.id in session.remaining_queue:
                in_queue = True
                idx = session.remaining_queue.index(user.id)
                queue_pos = f"POSITION_{idx + 1}"
            else:
                if data.position == "next":
                    session.remaining_queue.insert(0, user.id)
                    queue_pos = "NEXT_UP (#1)"
                else:
                    session.remaining_queue.append(user.id)
                    queue_pos = f"POSITION_{len(session.remaining_queue)}"

                await self.repository.update(session)
                await auction_redis.set_remaining_queue([str(uid) for uid in session.remaining_queue])

                in_queue = True

                # Broadcast queue update
                await auction_websocket.broadcast(
                    AuctionWebSocketEvent.SESSION_STARTED,
                    {
                        "session_id": str(session.id),
                        "status": session.status,
                        "remaining_count": len(session.remaining_queue),
                    },
                )

                await auction_activity_service.log_activity(
                    type="QUEUE_UPDATED",
                    title="Player Added to Queue ⚡",
                    description=f"{user.name} (#{user.roll_no or '—'}) added to live auction queue ({queue_pos})",
                    session_id=session.id,
                    player_id=user.id,
                    metadata={
                        "player_name": user.name,
                        "roll_no": user.roll_no,
                        "base_price": user.base_price,
                        "position": queue_pos,
                        "remaining_count": len(session.remaining_queue),
                    },
                )

            remaining_count = len(session.remaining_queue)
        elif session:
            remaining_count = len(session.remaining_queue)

        return {
            "user_id": str(user.id),
            "name": user.name,
            "roll_no": user.roll_no,
            "email": user.email,
            "base_price": user.base_price,
            "base_price_display": maroon_to_pushp(user.base_price),
            "image_url": user.image_url,
            "is_registered": user.is_registered,
            "in_queue": in_queue,
            "queue_position": queue_pos,
            "remaining_count": remaining_count,
            "message": f"Player '{user.name}' registered successfully" + (f" and placed into auction queue ({queue_pos})." if in_queue else "."),
        }
