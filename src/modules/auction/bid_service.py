import asyncio
from datetime import datetime, timezone
from typing import Any
import uuid

from beanie import PydanticObjectId

from src.core.database_transaction import mongo_transaction
from src.core.redis import redis_client
from src.modules.teams.wallet_constants import WalletTransactionType
from src.modules.teams.wallet_model import TeamWalletTransaction
from src.modules.team_assignments.model import TeamAssignment
from src.modules.users.model import User
from src.modules.auction.bid_model import AuctionBid
from src.modules.auction.constants import (
    BID_LADDER,
    AuctionSessionStatus,
    AuctionStatus,
)
from src.modules.auction.currency import maroon_to_pushp
from src.modules.auction.model import Auction
from src.modules.auction.redis_service import auction_redis
from src.modules.auction.session_model import AuctionSession
from src.modules.teams.model import Team
from src.common.websocket.websocket import auction_websocket, AuctionWebSocketEvent
from src.modules.auction.activity_log_service import auction_activity_service


class AuctionBidService:

    # ======================================================
    # PLACE BID (CONCURRENT 40-TEAM SAFE DISTRIBUTED MUTEX)
    # ======================================================

    async def place_bid(
        self,
        auction_id: PydanticObjectId,
        amount: int,
        team_id: PydanticObjectId | None = None,
    ) -> AuctionBid:

        # ------------------------------------------------------
        # 1. Distributed Redis Mutex Lock for High Concurrency
        # (Handles simultaneous bids from 40+ teams safely)
        # ------------------------------------------------------
        lock_key = f"auction:lock:bid:{str(auction_id)}"
        lock_token = str(uuid.uuid4())

        # Acquire lock (2500ms lease)
        acquired = await redis_client.set(lock_key, lock_token, nx=True, px=2500)
        if not acquired:
            # Fast backoff retry for simultaneous contenders
            for _ in range(8):
                await asyncio.sleep(0.035)
                acquired = await redis_client.set(lock_key, lock_token, nx=True, px=2500)
                if acquired:
                    break

            if not acquired:
                raise ValueError("Server is processing a simultaneous bid. Please retry next bid.")

        try:
            # --------------------------------------------------
            # 2. Check Global Bidding Lock State
            # --------------------------------------------------
            if not await auction_redis.is_bidding_enabled():
                raise ValueError("Bidding is currently locked by the auctioneer.")

            # --------------------------------------------------
            # 3. Fast Redis State Pre-check
            # (Immediately reject if current bid is already >= requested amount)
            # --------------------------------------------------
            redis_bid = await auction_redis.get_bid()
            current_redis_amount = redis_bid.get("amount", 0) if redis_bid else 0
            if current_redis_amount >= amount:
                raise ValueError(
                    f"Bid of {amount} M was already claimed by another team. Next higher bid is required."
                )

            async with mongo_transaction() as session:

                # --------------------------------------------------
                # 4. Validate Auction Document & Status
                # --------------------------------------------------
                auction = await Auction.get(
                    auction_id,
                    session=session,
                )

                if not auction:
                    raise ValueError("Auction document not found.")

                if auction.status != AuctionStatus.LIVE:
                    raise ValueError("Player is not live on the auction floor.")

                # --------------------------------------------------
                # 5. Validate Auction Session & Statuses
                # --------------------------------------------------
                auction_session = await AuctionSession.get(
                    auction.session_id,
                    session=session,
                )

                if not auction_session:
                    raise ValueError("Auction session not found.")

                if auction_session.status == AuctionSessionStatus.PAUSED:
                    raise ValueError("Auction session is currently paused.")
                elif auction_session.status == AuctionSessionStatus.ENDED:
                    raise ValueError("Auction session has ended.")
                elif auction_session.status != AuctionSessionStatus.LIVE:
                    raise ValueError("Auction session is not live.")

                # Verify current active student on floor
                if auction_session.current_auction_id != auction.id:
                    raise ValueError("This player is no longer the active student on the floor.")

                # --------------------------------------------------
                # 6. Validate Team Eligibility, Balance & Lead
                # --------------------------------------------------
                team = None
                if team_id:
                    team = await Team.get(
                        team_id,
                        session=session,
                    )

                    if not team:
                        raise ValueError("Team not found.")

                    if not team.is_active:
                        raise ValueError("Team is inactive.")

                    # Team cannot outbid itself consecutively
                    if auction.current_team_id == team.id:
                        raise ValueError(f"Your team ({team.name}) is already the leading bidder.")

                    # Check team wallet balance before bidding
                    if team.balance < amount:
                        raise ValueError(
                            f"Insufficient team budget. Team {team.name} has {team.balance} M remaining, but bid requires {amount} M."
                        )

                    # Check max 11 players per team
                    current_players_count = await User.find(
                        User.team_id == team.id,
                        session=session,
                    ).count()
                    if current_players_count >= 11:
                        raise ValueError(
                            f"Team squad is full ({current_players_count}/11 players). Maximum 11 players allowed per team."
                        )

                # --------------------------------------------------
                # 7. Strict Next Eligible Bid Ladder Calculation
                # (NO DIRECT JUMPS ALLOWED)
                # --------------------------------------------------
                next_eligible_bid = self._get_next_eligible_bid(
                    auction.base_price,
                    auction.current_bid,
                )

                if amount != next_eligible_bid:
                    raise ValueError(
                        f"Invalid bid {amount} M. Next eligible bid must strictly be {next_eligible_bid} M (direct level skips disallowed)."
                    )

                # --------------------------------------------------
                # 8. Create Immutable Bid Document
                # --------------------------------------------------
                bid = AuctionBid(
                    auction_id=auction.id,
                    team_id=team.id if team else None,
                    user_id=auction.user_id,
                    amount=amount,
                )

                await bid.insert(
                    session=session,
                )

                # --------------------------------------------------
                # 9. Advance Auction Floor Bid State
                # --------------------------------------------------
                auction.current_bid = amount
                if team:
                    auction.current_team_id = team.id

                await auction.save(
                    session=session,
                )

            # ------------------------------------------------------
            # 10. Mongo transaction committed.
            # Update Redis live state and broadcast WebSocket event
            # ------------------------------------------------------
            team_str = str(team.id) if team else (str(auction.current_team_id) if auction.current_team_id else "")

            await auction_redis.set_bid(
                amount,
                team_str,
            )

            await auction_redis.set_current_auction(
                {
                    "auction_id": str(auction.id),
                    "session_id": str(auction.session_id),
                    "user_id": str(auction.user_id),
                    "base_price": auction.base_price,
                    "current_bid": auction.current_bid,
                    "current_team_id": team_str if team_str else None,
                    "status": auction.status,
                }
            )

            await auction_websocket.broadcast(
                AuctionWebSocketEvent.BID,
                {
                    "auction_id": str(auction.id),
                    "bid_id": str(bid.id),
                    "team_id": str(team.id) if team else None,
                    "team_name": team.name if team else None,
                    "team_code": team.code if team else None,
                    "team_image_url": team.image_url if team else None,
                    "amount": amount,
                    "amount_display": maroon_to_pushp(amount),
                    "created_at": bid.created_at.isoformat() if bid.created_at else None,
                },
            )

            # Persist and broadcast live activity log
            await auction_activity_service.log_activity(
                type="BID",
                title="New Bid Placed",
                description=f"{team.name if team else 'Team'} placed bid of {amount} M",
                session_id=auction.session_id,
                auction_id=auction.id,
                metadata={
                    "amount": amount,
                    "amount_display": maroon_to_pushp(amount),
                    "team_id": str(team.id) if team else None,
                    "team_name": team.name if team else None,
                    "team_code": team.code if team else None,
                    "user_id": str(auction.user_id),
                },
            )

            return bid

        finally:
            # --------------------------------------------------
            # Release distributed mutex lock cleanly using token
            # --------------------------------------------------
            release_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            try:
                await redis_client.eval(release_script, 1, lock_key, lock_token)
            except Exception:
                pass

    # ======================================================
    # SELL PLAYER
    # ======================================================

    async def sell(
        self,
        auction_id: PydanticObjectId,
        created_by: PydanticObjectId,
        team_id: PydanticObjectId | None = None,
    ) -> Auction:

        async with mongo_transaction() as session:

            # --------------------------------------------------
            # 1. Get auction
            # --------------------------------------------------

            auction = await Auction.get(
                auction_id,
                session=session,
            )

            if not auction:
                raise ValueError("Auction not found")

            if auction.status != AuctionStatus.LIVE:
                raise ValueError("Auction is not live")

            # --------------------------------------------------
            # 2. Get auction session
            # --------------------------------------------------

            auction_session = await AuctionSession.get(
                auction.session_id,
                session=session,
            )

            if not auction_session:
                raise ValueError(
                    "Auction session not found"
                )

            if auction_session.status != AuctionSessionStatus.LIVE:
                raise ValueError(
                    "Auction session is not live"
                )

            # --------------------------------------------------
            # 3. Verify current auction
            # --------------------------------------------------

            if (
                auction_session.current_auction_id
                != auction.id
            ):
                raise ValueError(
                    "This is not the current auction"
                )

            # --------------------------------------------------
            # 4. A team must be assigned as the buyer
            # --------------------------------------------------

            winning_team_id = team_id or auction.current_team_id

            if winning_team_id is None:
                raise ValueError(
                    "Please select a winning squad to finalize the sale."
                )

            if auction.current_bid <= 0:
                raise ValueError(
                    "Invalid auction price"
                )

            # --------------------------------------------------
            # 5. Get winning team
            # --------------------------------------------------

            team = await Team.get(
                winning_team_id,
                session=session,
            )

            if not team:
                raise ValueError(
                    "Winning team not found"
                )

            if not team.is_active:
                raise ValueError(
                    "Winning team is not active"
                )

            # --------------------------------------------------
            # 6. Check balance & squad limit (Max 11 players)
            # --------------------------------------------------

            if team.balance < auction.current_bid:
                raise ValueError(
                    "Team does not have enough balance"
                )

            team_player_count = await User.find(
                User.team_id == team.id,
                session=session,
            ).count()
            if team_player_count >= 11:
                raise ValueError(
                    f"Winning team squad is full ({team_player_count}/11 players). Maximum 11 players allowed per team."
                )

            # --------------------------------------------------
            # 7. Get player
            # --------------------------------------------------

            user = await User.get(
                auction.user_id,
                session=session,
            )

            if not user:
                raise ValueError(
                    "Player not found"
                )

            if user.team_id is not None:
                raise ValueError(
                    "Player is already assigned to a team"
                )

            # --------------------------------------------------
            # 8. Calculate balance
            # --------------------------------------------------

            now = datetime.now(timezone.utc)

            balance_before = team.balance
            balance_after = (
                balance_before - auction.current_bid
            )

            # --------------------------------------------------
            # 9. Deduct team balance
            # --------------------------------------------------

            team.balance = balance_after

            await team.save(
                session=session,
            )

            # --------------------------------------------------
            # 10. Assign player
            # --------------------------------------------------

            user.team_id = team.id
            user.team_price = auction.current_bid
            user.updated_at = now

            await user.save(
                session=session,
            )

            # --------------------------------------------------
            # 11. Mark auction SOLD
            # --------------------------------------------------

            auction.status = AuctionStatus.SOLD
            auction.ended_at = now

            await auction.save(
                session=session,
            )

            # --------------------------------------------------
            # 12. Create team assignment
            # --------------------------------------------------

            assignment = TeamAssignment(
                user_id=user.id,
                team_id=team.id,
                price=auction.current_bid,
                assigned_at=now,
                assigned_by=created_by,
                is_current=True,
            )

            await assignment.insert(
                session=session,
            )

            # --------------------------------------------------
            # 13. Create wallet ledger
            # --------------------------------------------------

            wallet_transaction = TeamWalletTransaction(
                team_id=team.id,
                user_id=user.id,
                transaction_type=(
                    WalletTransactionType.AUCTION_PURCHASE
                ),
                amount=-auction.current_bid,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f"Player '{user.name}' purchased in auction",
                reference_id=str(auction.id),
                created_by=created_by,
            )

            await wallet_transaction.insert(
                session=session,
            )

            # --------------------------------------------------
            # 14. Clear current session player
            # --------------------------------------------------

            auction_session.current_user_id = None
            auction_session.current_auction_id = None

            await auction_session.save(
                session=session,
            )

        # ------------------------------------------------------
        # Mongo transaction committed.
        # ------------------------------------------------------

        await auction_redis.clear_current_auction()
        await auction_redis.set_bid(0, "")

        sold_count = await Auction.find(
            Auction.session_id == auction.session_id,
            Auction.status == AuctionStatus.SOLD,
        ).count()

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.PLAYER_SOLD,
            {
                "auction_id": str(auction.id),
                "user_id": str(user.id),
                "player_id": str(user.id),
                "player_name": user.name,
                "name": user.name,
                "roll_no": user.roll_no,
                "image_url": user.image_url,
                "base_price": auction.base_price,
                "base_price_display": maroon_to_pushp(auction.base_price),
                "team_id": str(team.id),
                "team_name": team.name,
                "team_code": team.code,
                "team_image_url": team.image_url,
                "team_balance": team.balance,
                "final_price": auction.current_bid,
                "winning_bid": auction.current_bid,
                "amount_display": maroon_to_pushp(auction.current_bid),
                "status": "SOLD",
                "sold_count": sold_count,
            },
        )

        # Persist and broadcast live activity log
        clean_name = f"{user.roll_no} - {user.name}" if user.roll_no else user.name
        await auction_activity_service.log_activity(
            type="SOLD",
            title="Player SOLD 🎉",
            description=f"{clean_name} SOLD to {team.name} for {auction.current_bid} M",
            session_id=auction.session_id,
            auction_id=auction.id,
            metadata={
                "player_id": str(user.id),
                "player_name": user.name,
                "roll_no": user.roll_no,
                "team_id": str(team.id),
                "team_name": team.name,
                "team_code": team.code,
                "amount": auction.current_bid,
                "amount_display": maroon_to_pushp(auction.current_bid),
            },
        )

        return auction

    # ======================================================
    # MARK UNSOLD
    # ======================================================

    async def mark_unsold(
        self,
        auction_id: PydanticObjectId,
    ) -> Auction:

        async with mongo_transaction() as session:

            # --------------------------------------------------
            # 1. Get auction
            # --------------------------------------------------

            auction = await Auction.get(
                auction_id,
                session=session,
            )

            if not auction:
                raise ValueError("Auction not found")

            if auction.status != AuctionStatus.LIVE:
                raise ValueError("Auction is not live")

            # --------------------------------------------------
            # 2. Get auction session
            # --------------------------------------------------

            auction_session = await AuctionSession.get(
                auction.session_id,
                session=session,
            )

            if not auction_session:
                raise ValueError(
                    "Auction session not found"
                )

            if auction_session.status != AuctionSessionStatus.LIVE:
                raise ValueError(
                    "Auction session is not live"
                )

            # --------------------------------------------------
            # 3. Update auction
            # --------------------------------------------------

            now = datetime.now(timezone.utc)
            auction.status = AuctionStatus.UNSOLD
            auction.ended_at = now

            await auction.save(
                session=session,
            )

            # --------------------------------------------------
            # 4. Move player to unsold queue
            # --------------------------------------------------

            if (
                auction.user_id
                not in auction_session.unsold_queue
            ):
                auction_session.unsold_queue.append(
                    auction.user_id
                )

            auction_session.current_auction_id = None
            auction_session.current_user_id = None

            await auction_session.save(
                session=session,
            )

        # ------------------------------------------------------
        # Mongo transaction committed.
        # ------------------------------------------------------

        await auction_redis.clear_current_auction()
        await auction_redis.set_bid(0, "")

        user = await User.get(auction.user_id)
        await auction_websocket.broadcast(
            AuctionWebSocketEvent.PLAYER_UNSOLD,
            {
                "auction_id": str(auction.id),
                "user_id": str(auction.user_id),
                "player_id": str(auction.user_id),
                "player_name": user.name if user else "Player",
                "name": user.name if user else "Player",
                "roll_no": user.roll_no if user else None,
                "image_url": user.image_url if user else None,
                "base_price": auction.base_price,
                "base_price_display": maroon_to_pushp(auction.base_price),
                "status": "UNSOLD",
            },
        )

        # Persist and broadcast live activity log
        clean_name = f"{user.roll_no} - {user.name}" if user and user.roll_no else (user.name if user else "Player")
        await auction_activity_service.log_activity(
            type="UNSOLD",
            title="Player UNSOLD",
            description=f"{clean_name} marked UNSOLD and moved to backup queue",
            session_id=auction.session_id,
            auction_id=auction.id,
            metadata={
                "player_id": str(auction.user_id),
                "player_name": user.name if user else "Player",
                "roll_no": user.roll_no if user else None,
            },
        )

        return auction

    # ======================================================
    # ROLLBACK BID
    # ======================================================

    async def rollback_bid(
        self,
        auction_id: PydanticObjectId,
        rolled_back_by: PydanticObjectId,
    ) -> dict[str, Any]:

        async with mongo_transaction() as session:

            # 1. Get auction
            auction = await Auction.get(
                auction_id,
                session=session,
            )

            if not auction:
                raise ValueError("Auction not found")

            if auction.status != AuctionStatus.LIVE:
                raise ValueError("Auction is not live")

            # 2. Get session
            auction_session = await AuctionSession.get(
                auction.session_id,
                session=session,
            )

            if not auction_session:
                raise ValueError("Auction session not found")

            if auction_session.status != AuctionSessionStatus.LIVE:
                raise ValueError("Auction session is not live")

            if auction_session.current_auction_id != auction.id:
                raise ValueError("This is not the current auction")

            # 3. Find all non-rolled-back bids for this auction, latest first
            bids = await AuctionBid.find(
                AuctionBid.auction_id == auction.id,
                AuctionBid.is_rolled_back == False,
                session=session,
            ).sort(
                "-created_at"
            ).to_list()

            if not bids:
                raise ValueError("No active bids to rollback")

            latest_bid = bids[0]
            now = datetime.now(timezone.utc)

            latest_bid.is_rolled_back = True
            latest_bid.rolled_back_at = now
            latest_bid.rolled_back_by = rolled_back_by

            await latest_bid.save(
                session=session,
            )

            # 4. Revert auction current bid
            if len(bids) > 1:
                prev_bid = bids[1]
                auction.current_bid = prev_bid.amount
                auction.current_team_id = prev_bid.team_id
            else:
                auction.current_bid = auction.base_price
                auction.current_team_id = None

            await auction.save(
                session=session,
            )

        # ------------------------------------------------------
        # Mongo transaction committed. Update Redis & broadcast.
        # ------------------------------------------------------

        redis_bid = auction.current_bid
        redis_team = str(auction.current_team_id) if auction.current_team_id else ""

        await auction_redis.set_bid(
            redis_bid,
            redis_team,
        )

        await auction_redis.set_current_auction(
            {
                "auction_id": str(auction.id),
                "session_id": str(auction.session_id),
                "user_id": str(auction.user_id),
                "base_price": auction.base_price,
                "current_bid": auction.current_bid,
                "current_team_id": redis_team if redis_team else None,
                "status": auction.status,
            }
        )

        await auction_websocket.broadcast(
            AuctionWebSocketEvent.BID_ROLLBACK,
            {
                "auction_id": str(auction.id),
                "rolled_back_bid_id": str(latest_bid.id),
                "rolled_back_amount": latest_bid.amount,
                "rolled_back_team_id": str(latest_bid.team_id),
                "current_bid": auction.current_bid,
                "current_bid_display": maroon_to_pushp(auction.current_bid),
                "current_team_id": redis_team if redis_team else None,
            },
        )

        return {
            "auction": auction,
            "rolled_back_bid": latest_bid,
        }

    # ======================================================
    # ROLLBACK SOLD PLAYER (UNDO SALE & REFUND WALLET)
    # ======================================================

    async def rollback_sold(
        self,
        auction_id: PydanticObjectId,
        rolled_back_by: PydanticObjectId,
    ) -> dict[str, Any]:

        async with mongo_transaction() as session:

            # 1. Get auction
            auction = await Auction.get(
                auction_id,
                session=session,
            )

            if not auction:
                raise ValueError("Auction not found")

            if auction.status != AuctionStatus.SOLD:
                raise ValueError("Only sold auctions can be rolled back")

            winning_team_id = auction.current_team_id
            if not winning_team_id:
                raise ValueError("Auction does not have a recorded winning team")

            # 2. Get winning team
            team = await Team.get(
                winning_team_id,
                session=session,
            )

            if not team:
                raise ValueError("Winning team not found")

            # 3. Get player
            user = await User.get(
                auction.user_id,
                session=session,
            )

            # 4. Refund winning team balance
            now = datetime.now(timezone.utc)
            balance_before = team.balance
            refund_amount = auction.current_bid
            balance_after = balance_before + refund_amount

            team.balance = balance_after
            await team.save(session=session)

            # 5. Insert AUCTION_ROLLBACK wallet ledger transaction
            wallet_transaction = TeamWalletTransaction(
                team_id=team.id,
                user_id=user.id if user else None,
                transaction_type=WalletTransactionType.AUCTION_ROLLBACK,
                amount=refund_amount,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f"Rollback sale of '{user.name if user else 'Player'}' in auction (Refund {refund_amount} M)",
                reference_id=str(auction.id),
                created_by=rolled_back_by,
            )
            await wallet_transaction.insert(session=session)

            # 6. Clear user's team assignment
            if user:
                user.team_id = None
                user.team_price = 0
                user.updated_at = now
                await user.save(session=session)

            # 7. Update TeamAssignment record if exists
            if user:
                assignment = await TeamAssignment.find_one(
                    TeamAssignment.user_id == user.id,
                    TeamAssignment.team_id == team.id,
                    TeamAssignment.is_current == True,
                    session=session,
                )
                if assignment:
                    assignment.is_current = False
                    assignment.removed_at = now
                    assignment.removed_by = rolled_back_by
                    await assignment.save(session=session)

            # 8. Mark auction as CANCELLED
            auction.status = AuctionStatus.CANCELLED
            await auction.save(session=session)

            # 9. If an active auction session exists, re-append player to unsold_queue
            auction_session = await AuctionSession.get(
                auction.session_id,
                session=session,
            )
            if auction_session and auction_session.status in [AuctionSessionStatus.LIVE, AuctionSessionStatus.PAUSED]:
                if user and (user.id not in auction_session.remaining_queue and user.id not in auction_session.unsold_queue):
                    auction_session.unsold_queue.append(user.id)
                    await auction_session.save(session=session)

        # Broadcast update to connected spectator and admin displays
        await auction_websocket.broadcast(
            AuctionWebSocketEvent.PLAYER_UNSOLD,
            {
                "auction_id": str(auction.id),
                "user_id": str(user.id) if user else "",
                "player_id": str(user.id) if user else "",
                "player_name": user.name if user else "Player",
                "name": user.name if user else "Player",
                "roll_no": user.roll_no if user else None,
                "image_url": user.image_url if user else None,
                "base_price": auction.base_price,
                "base_price_display": maroon_to_pushp(auction.base_price),
                "status": "CANCELLED",
                "message": f"Sale of {user.name if user else 'Player'} was rolled back",
            },
        )

        # Persist and broadcast live activity log
        clean_name = f"{user.roll_no} - {user.name}" if user and user.roll_no else (user.name if user else "Player")
        await auction_activity_service.log_activity(
            type="BID_ROLLBACK",
            title="Sale Rolled Back",
            description=f"Sale of {clean_name} to {team.name} rolled back ({refund_amount} M refunded)",
            session_id=auction.session_id,
            auction_id=auction.id,
            metadata={
                "player_id": str(user.id) if user else "",
                "player_name": user.name if user else "Player",
                "team_id": str(team.id),
                "team_name": team.name,
                "refund_amount": refund_amount,
                "refund_amount_display": maroon_to_pushp(refund_amount),
            },
        )

        return {
            "auction_id": str(auction.id),
            "status": auction.status,
            "refund_amount": refund_amount,
            "refund_amount_display": maroon_to_pushp(refund_amount),
            "team_id": str(team.id),
            "team_name": team.name,
            "user_id": str(user.id) if user else "",
            "user_name": user.name if user else "",
        }

    # ======================================================
    # FIND NEXT VALID BID
    # ======================================================

    @staticmethod
    def _get_next_eligible_bid(
        base_price: int,
        current_bid: int,
    ) -> int:
        """
        Calculates strictly the exact next step on the BID_LADDER.
        Ladder: 5, 10, 15, 20, 25, 50, 75, 100, 125, 175, 225, 275, 325, 425,
                525, 625, 750, 875, 1000, 1150, 1300, 1450, 1600, 1800, 2000,
                2500, 3125, 3750, 4375, 5000
        Direct jumps across ladder levels are strictly prohibited.
        """
        # If no bids have been placed yet on this floor appearance:
        if current_bid == 0 or current_bid < base_price:
            for bid in BID_LADDER:
                if bid >= base_price:
                    return bid
            return BID_LADDER[-1]

        # Next bid MUST strictly be the smallest ladder step strictly greater than current_bid
        for bid in BID_LADDER:
            if bid > current_bid:
                return bid

        raise ValueError("Maximum bid ladder limit (5000 M) has been reached")

    @staticmethod
    def _get_minimum_bid(
        base_price: int,
        current_bid: int,
    ) -> int:
        return AuctionBidService._get_next_eligible_bid(base_price, current_bid)