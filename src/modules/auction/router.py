from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from beanie import PydanticObjectId

from src.common.websocket.manager import websocket_manager
from src.modules.users.model import User
from src.modules.teams.model import Team
from src.modules.registration.model import Registration

from src.modules.auction.bid_model import AuctionBid
from src.modules.auction.bid_service import AuctionBidService
from src.modules.auction.constants import AuctionSessionStatus, AuctionStatus
from src.modules.auction.currency import maroon_to_pushp
from src.modules.auction.model import Auction
from src.modules.auction.redis_service import auction_redis
from src.modules.auction.schema import (
    AuctionBidResponse,
    AuctionLiveResponse,
    AuctionResponse,
    PlaceBidRequest,
    SellPlayerRequest,
    RollbackBidResponse,
    ToggleBiddingRequest,
    PublicAuctionLiveResponse,
    PublicBidItem,
    PublicPlayerInfo,
    PublicRecentActivityItem,
    PublicRosterPlayer,
    PublicSessionInfo,
    PublicTeamRosterResponse,
    PublicTeamSummary,
    QuickAddPlayerRequest,
    QuickAddPlayerResponse,
)
from src.modules.auction.session_schema import (
    AuctionSessionResponse,
    AuctionSessionStartRequest,
    AuctionSessionResumeRequest,
    ReorderQueueRequest,
)
from src.modules.auction.session_service import AuctionSessionService
from src.modules.auth.dependencies import require_superuser, get_current_user, require_permission


router = APIRouter(
    prefix="/auction",
    tags=["auction"],
)

bid_service = AuctionBidService()
session_service = AuctionSessionService()

# ==========================================================
# HELPERS
# ==========================================================

def auction_to_response(
    auction: Auction,
) -> AuctionResponse:
    return AuctionResponse(
        id=str(auction.id),
        user_id=str(auction.user_id),
        base_price=auction.base_price,
        base_price_display=maroon_to_pushp(auction.base_price),
        status=auction.status,
        current_bid=auction.current_bid,
        current_bid_display=maroon_to_pushp(auction.current_bid),
        current_team_id=(
            str(auction.current_team_id)
            if auction.current_team_id
            else None
        ),
        started_at=auction.started_at,
        ended_at=auction.ended_at,
    )


def session_to_response(
    session,
) -> AuctionSessionResponse:
    return AuctionSessionResponse(
        id=str(session.id),
        status=session.status,
        sort_by=session.sort_by,
        sort_direction=session.sort_direction,
        remaining_count=len(session.remaining_queue),
        unsold_count=len(session.unsold_queue),
        current_user_id=(
            str(session.current_user_id)
            if session.current_user_id
            else None
        ),
        current_auction_id=(
            str(session.current_auction_id)
            if session.current_auction_id
            else None
        ),
        started_at=session.started_at,
        paused_at=session.paused_at,
        ended_at=session.ended_at,
    )


def parse_object_id(
    value: str,
    field_name: str,
) -> PydanticObjectId:
    if not PydanticObjectId.is_valid(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        )
    return PydanticObjectId(value)


# ==========================================================
# WEBSOCKET REAL-TIME STREAM (PUBLIC, NO AUTH)
# ==========================================================

@router.websocket("/ws")
async def auction_websocket_endpoint(
    websocket: WebSocket,
    client_type: str = Query(default="public"),
    token: str | None = Query(default=None),
):
    """
    WebSocket stream for auction live screen and spectators.
    client_type: 'public' (spectator/display) or 'admin' (admin desk/management)
    """
    await websocket_manager.connect(websocket, client_type=client_type)
    from src.common.websocket.websocket import auction_websocket, AuctionWebSocketEvent

    # Broadcast updated public spectator count to all connected clients
    await auction_websocket.broadcast(
        AuctionWebSocketEvent.VIEWER_COUNT,
        {
            "viewer_count": websocket_manager.connection_count,
            "bidding_enabled": await auction_redis.is_bidding_enabled(),
        },
    )
    try:
        while True:
            # Keep connection alive; can accept client heartbeats/pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        await auction_websocket.broadcast(
            AuctionWebSocketEvent.VIEWER_COUNT,
            {
                "viewer_count": websocket_manager.connection_count,
                "bidding_enabled": await auction_redis.is_bidding_enabled(),
            },
        )
    except Exception:
        websocket_manager.disconnect(websocket)
        await auction_websocket.broadcast(
            AuctionWebSocketEvent.VIEWER_COUNT,
            {
                "viewer_count": websocket_manager.connection_count,
                "bidding_enabled": await auction_redis.is_bidding_enabled(),
            },
        )


# ==========================================================
# PUBLIC SCREEN APIS (NO AUTHENTICATION REQUIRED)
# ==========================================================

@router.get(
    "/public/live",
    response_model=PublicAuctionLiveResponse,
)
async def get_public_live_state():
    """
    Public API for spectator screens / big displays to see the live auction
    without authentication.
    """
    bidding_enabled = await auction_redis.is_bidding_enabled()
    viewer_count = websocket_manager.connection_count

    session = await session_service.repository.get_current()
    if not session:
        return PublicAuctionLiveResponse(
            session=None,
            player=None,
            status="idle",
            timer=None,
            viewer_count=viewer_count,
            bidding_enabled=bidding_enabled,
        )

    session_info = PublicSessionInfo(
        id=str(session.id),
        status=session.status,
        remaining_count=len(session.remaining_queue),
        unsold_count=len(session.unsold_queue),
        started_at=session.started_at,
    )

    current = await auction_redis.get_current_auction()
    bid = await auction_redis.get_bid()
    timer = await auction_redis.get_timer()
    redis_status = await auction_redis.get_status()

    if not current:
        return PublicAuctionLiveResponse(
            session=session_info,
            player=None,
            status=redis_status or session.status,
            timer=timer,
            viewer_count=viewer_count,
            bidding_enabled=bidding_enabled,
        )

    # Fetch player details
    player_id_str = current.get("user_id")
    player_info: PublicPlayerInfo | None = None
    if player_id_str and PydanticObjectId.is_valid(player_id_str):
        user = await User.get(PydanticObjectId(player_id_str))
        if user:
            base_price = current.get("base_price", user.base_price)
            sports_data = None
            reg = await Registration.find_one(Registration.user_id == user.id)
            if reg:
                sports_data = reg.sports_map
            player_info = PublicPlayerInfo(
                id=str(user.id),
                name=user.name,
                roll_no=user.roll_no,
                image_url=user.image_url,
                base_price=base_price,
                base_price_display=maroon_to_pushp(base_price),
                sports=sports_data,
                games=reg.games if reg else [],
                experience_years=reg.experience_years if reg else None,
                critical_situation=reg.critical_situation if reg else [],
                creative_talent=reg.creative_talent if reg else [],
                sportsmanship=reg.sportsmanship if reg else [],
                preference=reg.preference if reg else [],
                questions={
                    "games": reg.games if reg else [],
                    "experience_years": reg.experience_years if reg else None,
                    "critical_situation": reg.critical_situation if reg else [],
                    "creative_talent": reg.creative_talent if reg else [],
                    "sportsmanship": reg.sportsmanship if reg else [],
                    "preference": reg.preference if reg else [],
                } if reg else None,
            )

    # Current bid & leading team
    current_bid = bid.get("amount") if bid and bid.get("amount") else current.get("current_bid", 0)
    current_team_id_str = bid.get("team_id") if bid and bid.get("team_id") else current.get("current_team_id")

    team_info: PublicTeamSummary | None = None
    if current_team_id_str and PydanticObjectId.is_valid(current_team_id_str):
        team = await Team.get(PydanticObjectId(current_team_id_str))
        if team:
            team_info = PublicTeamSummary(
                id=str(team.id),
                name=team.name,
                code=team.code,
                image_url=team.image_url,
            )

    # Fetch active bids for this auction attempt
    recent_bids: list[PublicBidItem] = []
    auction_id_str = current.get("auction_id")
    if auction_id_str and PydanticObjectId.is_valid(auction_id_str):
        bids = await AuctionBid.find(
            AuctionBid.auction_id == PydanticObjectId(auction_id_str),
            AuctionBid.is_rolled_back == False,
        ).sort("-created_at").limit(10).to_list()

        for b in bids:
            b_team = await Team.get(b.team_id)
            recent_bids.append(
                PublicBidItem(
                    id=str(b.id),
                    team_id=str(b.team_id),
                    team_name=b_team.name if b_team else "Unknown",
                    team_code=b_team.code if b_team else "???",
                    team_image_url=b_team.image_url if b_team else None,
                    amount=b.amount,
                    amount_display=maroon_to_pushp(b.amount),
                    created_at=b.created_at,
                )
            )

    # If the public screen is in STANDBY or IDLE, do not display the player
    if redis_status == "STANDBY" or redis_status == "IDLE":
        player_info = None

    return PublicAuctionLiveResponse(
        auction_id=current.get("auction_id") if current else None,
        session=session_info,
        player=player_info,
        current_bid=current_bid,
        current_bid_display=maroon_to_pushp(current_bid) if current_bid else "0 M",
        current_team=team_info,
        status=redis_status or current.get("status") or session.status,
        timer=timer,
        recent_bids=recent_bids,
        viewer_count=viewer_count,
        bidding_enabled=bidding_enabled,
    )


@router.get(
    "/public/teams",
    response_model=list[PublicTeamRosterResponse],
)
async def get_public_teams():
    """
    Public API for displaying all teams with remaining budget and roster list.
    No authentication required.
    """
    teams = await Team.find(Team.is_active == True).sort("code").to_list()
    result: list[PublicTeamRosterResponse] = []

    for team in teams:
        members = await User.find(User.team_id == team.id).to_list()

        captain_user = None
        vice_captain_user = None

        for u in members:
            if team.captain_id and u.id == team.captain_id:
                captain_user = u
            if team.vice_captain_id and u.id == team.vice_captain_id:
                vice_captain_user = u

        if team.captain_id and not captain_user:
            captain_user = await User.get(team.captain_id)
        if team.vice_captain_id and not vice_captain_user:
            vice_captain_user = await User.get(team.vice_captain_id)

        roster = [
            PublicRosterPlayer(
                id=str(u.id),
                name=u.name,
                roll_no=u.roll_no,
                price=u.team_price,
                price_display=maroon_to_pushp(u.team_price),
                image_url=u.image_url,
                mobile=u.mobile,
                is_captain=(team.captain_id is not None and u.id == team.captain_id),
                is_vice_captain=(team.vice_captain_id is not None and u.id == team.vice_captain_id),
            )
            for u in members
        ]

        result.append(
            PublicTeamRosterResponse(
                id=str(team.id),
                name=team.name,
                code=team.code,
                image_url=team.image_url,
                captain_id=str(team.captain_id) if team.captain_id else None,
                captain_name=captain_user.name if captain_user else None,
                captain_mobile=captain_user.mobile if captain_user else None,
                captain_image_url=captain_user.image_url if captain_user else None,
                vice_captain_id=str(team.vice_captain_id) if team.vice_captain_id else None,
                vice_captain_name=vice_captain_user.name if vice_captain_user else None,
                vice_captain_mobile=vice_captain_user.mobile if vice_captain_user else None,
                vice_captain_image_url=vice_captain_user.image_url if vice_captain_user else None,
                initial_balance=team.initial_balance,
                initial_balance_display=maroon_to_pushp(team.initial_balance),
                balance=team.balance,
                balance_display=maroon_to_pushp(team.balance),
                players_count=len(roster),
                players=roster,
            )
        )

    return result


@router.get(
    "/public/recent",
    response_model=list[PublicRecentActivityItem],
)
async def get_public_recent_activity():
    """
    Public API to display recently sold or unsold players.
    No authentication required.
    """
    auctions = await Auction.find(
        {"status": {"$in": [AuctionStatus.SOLD, AuctionStatus.UNSOLD]}}
    ).sort("-ended_at").limit(20).to_list()

    items: list[PublicRecentActivityItem] = []
    for a in auctions:
        user = await User.get(a.user_id)
        team = await Team.get(a.current_team_id) if a.current_team_id else None

        items.append(
            PublicRecentActivityItem(
                auction_id=str(a.id),
                player_id=str(a.user_id),
                player_name=user.name if user else "Unknown Player",
                roll_no=user.roll_no if user else None,
                image_url=user.image_url if user else None,
                base_price=a.base_price,
                base_price_display=maroon_to_pushp(a.base_price),
                status=a.status,
                final_price=a.current_bid if a.status == AuctionStatus.SOLD else None,
                final_price_display=maroon_to_pushp(a.current_bid) if a.status == AuctionStatus.SOLD else None,
                winning_team_id=str(team.id) if team else None,
                winning_team_name=team.name if team else None,
                winning_team_code=team.code if team else None,
                ended_at=a.ended_at,
            )
        )

    return items


# ==========================================================
# ADMIN AUCTION SESSION CONTROLS (REQUIRE SUPERUSER)
# ==========================================================

@router.post(
    "/start",
    response_model=AuctionSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_auction(
    request: AuctionSessionStartRequest,
    current_user: User = Depends(require_permission("auction:start")),
):
    try:
        session = await session_service.start(
            sort_by=request.sort_by,
            sort_direction=request.sort_direction,
        )
        return session_to_response(session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/session/current",
    response_model=AuctionSessionResponse,
)
async def get_current_session(
    current_user: User = Depends(require_permission("auction:view")),
):
    session = await session_service.repository.get_current()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active auction session",
        )
    return session_to_response(session)


@router.post(
    "/session/queue/csv",
)
async def import_auction_queue_csv(
    file: UploadFile = File(...),
    auto_start: bool = Query(default=False),
    append_mode: bool = Query(default=False),
    current_user: User = Depends(require_permission("auction:update")),
):
    """
    Upload CSV with roll_no order to create or reorder the live auction queue.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a CSV file (.csv)",
        )

    content = await file.read()
    try:
        result = await session_service.import_queue_from_csv(
            file_content=content,
            auto_start=auto_start,
            append_mode=append_mode,
        )
        return {
            "success": True,
            "message": f"Auction queue successfully configured with {result.get('matched_count', 0)} players from CSV.",
            "data": result,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV processing failed: {str(exc)}",
        )


@router.post(
    "/session/{session_id}/next",
    response_model=AuctionResponse | None,
)
async def next_player(
    session_id: str,
    current_user: User = Depends(require_permission("auction:start")),
):
    session_object_id = parse_object_id(
        session_id,
        "session ID",
    )

    try:
        session = await session_service.repository.get_by_id(
            session_object_id
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auction session not found",
            )

        auction = await session_service.get_next_player(
            session
        )
        if auction is None:
            return None

        return auction_to_response(auction)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/session/upcoming",
)
async def get_upcoming_players(
    limit: int = 2,
    current_user: User = Depends(require_permission("auction:view")),
):
    """
    Fetch upcoming players in queue for floor staging preview.
    """
    return await session_service.get_upcoming_players(limit=limit)


@router.get(
    "/session/queue",
)
async def get_full_auction_queue(
    current_user: User = Depends(require_permission("auction:view")),
):
    """
    Fetch full detailed auction queue with student profiles (remaining & unsold).
    """
    return await session_service.get_full_queue()


@router.put(
    "/session/queue/reorder",
)
async def reorder_auction_queue(
    request: ReorderQueueRequest,
    current_user: User = Depends(require_permission("auction:update")),
):
    """
    Persist reordered remaining queue sequence from admin drag-and-drop.
    """
    try:
        return await session_service.reorder_queue(user_ids=request.user_ids)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete(
    "/session/queue/{user_id}",
)
async def remove_player_from_auction_queue(
    user_id: str,
    current_user: User = Depends(require_permission("auction:update")),
):
    """
    Remove a student from the active auction queue.
    """
    try:
        return await session_service.remove_from_queue(user_id=user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/session/queue/requeue-unsold",
)
async def requeue_unsold_players(
    user_id: str | None = Query(None, description="Optional specific user ID to re-queue"),
    current_user: User = Depends(require_permission("auction:update")),
):
    """
    Move unsold student(s) back into the active remaining queue.
    """
    try:
        return await session_service.requeue_unsold(user_id=user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/session/quick-add-player",
    response_model=QuickAddPlayerResponse,
)
async def quick_add_player_to_auction(
    request: QuickAddPlayerRequest,
    current_user: User = Depends(require_permission("auction:update")),
):
    """
    On-the-fly player registration and live auction queue injection.
    Creates user account, registers questionnaire profile, sets base price,
    and inserts player into the active auction session's remaining queue.
    """
    try:
        result = await session_service.quick_add_player(
            data=request,
            created_by=current_user.id,
        )
        return QuickAddPlayerResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/session/floor",
)
async def get_admin_floor_state(
    current_user: User = Depends(require_permission("auction:view")),
):
    """
    Fetch comprehensive floor review state for Admin command console.
    Returns the staged player even when public screen is on STANDBY.
    """
    session = await session_service.repository.get_current()
    if not session:
        return {"session": None, "player": None, "status": "PENDING"}

    current = await auction_redis.get_current_auction()
    bid = await auction_redis.get_bid()
    redis_status = await auction_redis.get_status()

    player_info = None
    if current and current.get("user_id") and PydanticObjectId.is_valid(current.get("user_id")):
        user = await User.get(PydanticObjectId(current["user_id"]))
        if user:
            base_price = current.get("base_price", user.base_price)
            sports_data = None
            reg = await Registration.find_one(Registration.user_id == user.id)
            if reg:
                sports_data = reg.sports_map
            player_info = {
                "id": str(user.id),
                "name": user.name,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "roll_no": user.roll_no,
                "image_url": user.image_url,
                "base_price": base_price,
                "base_price_display": maroon_to_pushp(base_price),
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

    current_bid = bid.get("amount") if bid and bid.get("amount") else (current.get("current_bid", 0) if current else 0)
    current_team_id_str = bid.get("team_id") if bid and bid.get("team_id") else (current.get("current_team_id") if current else None)

    team_info = None
    if current_team_id_str and PydanticObjectId.is_valid(current_team_id_str):
        team = await Team.get(PydanticObjectId(current_team_id_str))
        if team:
            team_info = {
                "id": str(team.id),
                "name": team.name,
                "code": team.code,
                "image_url": team.image_url,
            }

    return {
        "session": session_to_response(session),
        "player": player_info,
        "current_auction_id": current.get("auction_id") if current else None,
        "current_bid": current_bid,
        "current_team": team_info,
        "is_displayed": (redis_status == "LIVE"),
        "status": redis_status or "STANDBY",
        "viewer_count": websocket_manager.connection_count,
        "bidding_enabled": await auction_redis.is_bidding_enabled(),
    }


@router.post(
    "/session/display-player",
)
async def display_player_on_public_screen(
    current_user: User = Depends(require_permission("auction:update")),
):
    """
    Publish staged player to the public auction display.
    """
    from src.common.websocket.websocket import auction_websocket, AuctionWebSocketEvent
    from src.modules.auction.activity_log_service import auction_activity_service
    current = await auction_redis.get_current_auction()
    if not current or not current.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No player currently staged to display",
        )

    await auction_redis.set_status("LIVE")
    user = await User.get(PydanticObjectId(current["user_id"]))
    if user:
        player_dict = {
            "id": str(user.id),
            "name": user.name,
            "roll_no": user.roll_no,
            "image_url": user.image_url,
            "base_price": current.get("base_price", user.base_price),
            "base_price_display": maroon_to_pushp(current.get("base_price", user.base_price)),
        }
        await auction_websocket.broadcast(
            AuctionWebSocketEvent.PLAYER_STARTED,
            {
                "auction_id": current.get("auction_id"),
                "player": player_dict,
                "base_price": current.get("base_price", user.base_price),
                "status": "LIVE",
                "is_staged": False,
            },
        )
        # Log to activity log
        clean_name = f"{user.roll_no} - {user.name}" if user.roll_no else user.name
        session_oid = PydanticObjectId(current.get("session_id")) if current.get("session_id") and PydanticObjectId.is_valid(current.get("session_id")) else None
        auction_oid = PydanticObjectId(current.get("auction_id")) if current.get("auction_id") and PydanticObjectId.is_valid(current.get("auction_id")) else None
        await auction_activity_service.log_activity(
            type="DISPLAY_LIVE",
            title="Player Put on Live Display 📺",
            description=f"{clean_name} is now LIVE on public spectator displays",
            session_id=session_oid,
            auction_id=auction_oid,
            metadata={"player_id": str(user.id), "player_name": user.name, "roll_no": user.roll_no},
        )
    return {"success": True, "message": "Player displayed on public screen"}


@router.post(
    "/session/off-player",
)
async def off_player_from_public_screen(
    current_user: User = Depends(require_permission("auction:update")),
):
    """
    Hide player from the public auction screen and place stage in standby.
    """
    from src.common.websocket.websocket import auction_websocket, AuctionWebSocketEvent
    from src.modules.auction.activity_log_service import auction_activity_service
    await auction_redis.set_status("STANDBY")
    await auction_websocket.broadcast(
        AuctionWebSocketEvent.PLAYER_UNSOLD,
        {"status": "STANDBY", "player": None},
    )
    current = await auction_redis.get_current_auction()
    session_oid = PydanticObjectId(current.get("session_id")) if current and current.get("session_id") and PydanticObjectId.is_valid(current.get("session_id")) else None
    auction_oid = PydanticObjectId(current.get("auction_id")) if current and current.get("auction_id") and PydanticObjectId.is_valid(current.get("auction_id")) else None
    await auction_activity_service.log_activity(
        type="DISPLAY_STANDBY",
        title="Screen Standby 🛡️",
        description="Public display placed on Standby mode by auction admin",
        session_id=session_oid,
        auction_id=auction_oid,
    )
    return {"success": True, "message": "Stage placed in standby mode"}


@router.post(
    "/session/{session_id}/pause",
    response_model=AuctionSessionResponse,
)
async def pause_auction(
    session_id: str,
    current_user: User = Depends(require_permission("auction:pause")),
):
    session_object_id = parse_object_id(
        session_id,
        "session ID",
    )

    try:
        session = await session_service.pause(
            session_object_id
        )
        return session_to_response(session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/session/{session_id}/resume",
    response_model=AuctionSessionResponse,
)
async def resume_auction(
    session_id: str,
    request: AuctionSessionResumeRequest | None = None,
    current_user: User = Depends(require_permission("auction:start")),
):
    session_object_id = parse_object_id(
        session_id,
        "session ID",
    )

    try:
        session = await session_service.resume(
            session_id=session_object_id,
            sort_by=request.sort_by if request else None,
            sort_direction=(
                request.sort_direction
                if request
                else None
            ),
        )
        return session_to_response(session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/session/{session_id}/end",
    response_model=AuctionSessionResponse,
)
async def end_auction(
    session_id: str,
    current_user: User = Depends(require_permission("auction:end")),
):
    session_object_id = parse_object_id(
        session_id,
        "session ID",
    )

    try:
        session = await session_service.end(
            session_object_id
        )
        return session_to_response(session)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/session/bidding/toggle",
)
async def toggle_bidding(
    request: ToggleBiddingRequest | None = None,
    current_user: User = Depends(require_permission("auction:update")),
):
    """
    Enable or disable bidding during live auction.
    """
    from src.modules.auction.activity_log_service import auction_activity_service

    if request and request.enabled is not None:
        target_state = request.enabled
    else:
        current_state = await auction_redis.is_bidding_enabled()
        target_state = not current_state

    await auction_redis.set_bidding_enabled(target_state)

    from src.common.websocket.websocket import auction_websocket, AuctionWebSocketEvent
    await auction_websocket.broadcast(
        AuctionWebSocketEvent.BIDDING_TOGGLED,
        {
            "bidding_enabled": target_state,
            "status": "BIDDING_OPEN" if target_state else "BIDDING_LOCKED",
        },
    )

    current = await auction_redis.get_current_auction()
    session_oid = PydanticObjectId(current.get("session_id")) if current and current.get("session_id") and PydanticObjectId.is_valid(current.get("session_id")) else None
    auction_oid = PydanticObjectId(current.get("auction_id")) if current and current.get("auction_id") and PydanticObjectId.is_valid(current.get("auction_id")) else None

    await auction_activity_service.log_activity(
        type="BIDDING_TOGGLED",
        title="Bidding " + ("Unlocked 🔓" if target_state else "Locked 🔒"),
        description=f"Captains bidding {'ENABLED' if target_state else 'LOCKED'} by auctioneer",
        session_id=session_oid,
        auction_id=auction_oid,
        metadata={"bidding_enabled": target_state},
    )

    return {
        "success": True,
        "bidding_enabled": target_state,
        "message": f"Bidding {'enabled' if target_state else 'disabled'} successfully",
    }


# ==========================================================
# LIVE AUCTION STATE (FAST INTERNAL/CLIENT POLLING)
# ==========================================================

@router.get(
    "/live",
    response_model=AuctionLiveResponse,
)
async def get_live_auction():
    session = await session_service.repository.get_current()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active auction session",
        )

    bidding_enabled = await auction_redis.is_bidding_enabled()
    viewer_count = websocket_manager.connection_count

    current = await auction_redis.get_current_auction()
    bid = await auction_redis.get_bid()
    timer = await auction_redis.get_timer()
    redis_status = await auction_redis.get_status()

    if not current:
        return AuctionLiveResponse(
            status=redis_status or session.status,
            timer=timer,
            viewer_count=viewer_count,
            bidding_enabled=bidding_enabled,
        )

    return AuctionLiveResponse(
        auction_id=current.get("auction_id"),
        user_id=current.get("user_id"),
        base_price=current.get("base_price"),
        base_price_display=maroon_to_pushp(current.get("base_price", 0)),
        current_bid=(
            bid.get("amount")
            if bid
            else current.get("current_bid")
        ),
        current_bid_display=maroon_to_pushp(
            bid.get("amount") if bid else current.get("current_bid", 0)
        ),
        current_team_id=(
            bid.get("team_id")
            if bid
            else current.get("current_team_id")
        ),
        status=redis_status or current.get("status"),
        timer=timer,
        viewer_count=viewer_count,
        bidding_enabled=bidding_enabled,
    )


# ==========================================================
# BID & PLAYER CONTROLS (REQUIRE SUPERUSER)
# ==========================================================

@router.post(
    "/{auction_id}/bid",
    response_model=AuctionBidResponse,
)
async def place_bid(
    auction_id: str,
    request: PlaceBidRequest,
    current_user: User = Depends(get_current_user),
):
    auction_object_id = parse_object_id(
        auction_id,
        "auction ID",
    )

    team_object_id = (
        parse_object_id(request.team_id, "team ID")
        if request.team_id
        else None
    )

    # Check if bidding is enabled
    is_enabled = await auction_redis.is_bidding_enabled()
    if not is_enabled and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bidding is currently locked by the auctioneer",
        )

    # Check authorization: superuser, auction:bid permission, or Captain/Vice-Captain
    from src.modules.auth.dependencies import check_user_permission
    has_bid_perm = await check_user_permission(current_user, "auction:bid")

    if not current_user.is_superuser and not has_bid_perm:
        # Find if user is captain or vice-captain of a team
        user_team = await Team.find_one({
            "$or": [
                {"captain_id": current_user.id},
                {"vice_captain_id": current_user.id},
            ],
            "is_active": True,
        })
        if not user_team:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team captains, vice-captains, or auction officials can place bids",
            )
        if team_object_id and team_object_id != user_team.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only place bids for your own team",
            )
        team_object_id = user_team.id

    try:
        bid = await bid_service.place_bid(
            auction_id=auction_object_id,
            team_id=team_object_id,
            amount=request.amount,
        )

        return AuctionBidResponse(
            id=str(bid.id),
            auction_id=str(bid.auction_id),
            team_id=str(bid.team_id) if bid.team_id else None,
            user_id=str(bid.user_id),
            amount=bid.amount,
            amount_display=maroon_to_pushp(bid.amount),
            created_at=bid.created_at,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{auction_id}/rollback-bid",
    response_model=RollbackBidResponse,
)
async def rollback_bid(
    auction_id: str,
    current_user: User = Depends(require_permission("auction:rollback")),
):
    """
    Rollback the latest active bid on the current auction attempt.
    Reverts current price to the previous bid (or base price).
    """
    auction_object_id = parse_object_id(
        auction_id,
        "auction ID",
    )

    try:
        result = await bid_service.rollback_bid(
            auction_id=auction_object_id,
            rolled_back_by=current_user.id,
        )

        auction = result["auction"]
        rolled_back_bid = result["rolled_back_bid"]

        return RollbackBidResponse(
            auction_id=str(auction.id),
            status=auction.status,
            current_bid=auction.current_bid,
            current_bid_display=maroon_to_pushp(auction.current_bid),
            current_team_id=str(auction.current_team_id) if auction.current_team_id else None,
            rolled_back_bid_id=str(rolled_back_bid.id),
            rolled_back_amount=rolled_back_bid.amount,
            rolled_back_amount_display=maroon_to_pushp(rolled_back_bid.amount),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{auction_id}/rollback",
)
async def rollback_sold_auction(
    auction_id: str,
    current_user: User = Depends(require_permission("auction:rollback")),
):
    """
    Rollback a completed SOLD auction attempt.
    Refunds the winning team's wallet balance, creates an AUCTION_ROLLBACK
    ledger transaction, clears player team assignment, marks auction CANCELLED,
    and re-queues player.
    """
    auction_object_id = parse_object_id(
        auction_id,
        "auction ID",
    )

    try:
        result = await bid_service.rollback_sold(
            auction_id=auction_object_id,
            rolled_back_by=current_user.id,
        )
        return {
            "success": True,
            "message": f"Sale of {result.get('user_name', 'player')} rolled back successfully. {result.get('team_name')} refunded {result.get('refund_amount_display')}.",
            "data": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{auction_id}/sell",
    response_model=AuctionResponse,
)
async def sell_player(
    auction_id: str,
    request: SellPlayerRequest | None = None,
    current_user: User = Depends(require_permission("auction:sell")),
):
    auction_object_id = parse_object_id(
        auction_id,
        "auction ID",
    )

    team_object_id = (
        parse_object_id(request.team_id, "team ID")
        if request and request.team_id
        else None
    )

    try:
        auction = await bid_service.sell(
            auction_id=auction_object_id,
            created_by=current_user.id,
            team_id=team_object_id,
        )
        return auction_to_response(auction)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{auction_id}/unsold",
    response_model=AuctionResponse,
)
async def mark_unsold(
    auction_id: str,
    current_user: User = Depends(require_permission("auction:sell")),
):
    auction_object_id = parse_object_id(
        auction_id,
        "auction ID",
    )

    try:
        auction = await bid_service.mark_unsold(
            auction_id=auction_object_id,
        )
        return auction_to_response(auction)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ==========================================================
# AUCTION ACTIVITY LOGS (MANAGEMENT AUDIT STREAM)
# Must be defined BEFORE /{auction_id} to avoid route collision
# ==========================================================

@router.get(
    "/activity-logs",
)
async def get_activity_logs(
    session_id: str | None = None,
    type: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_permission("auction:view")),
):
    """
    Fetch comprehensive activity logs stream for management console.
    Stored in Redis & permanent MongoDB.
    """
    from src.modules.auction.activity_log_service import auction_activity_service

    session_oid = parse_object_id(session_id, "session ID") if (session_id and PydanticObjectId.is_valid(session_id)) else None
    logs = await auction_activity_service.get_logs(
        session_id=session_oid,
        type=type,
        limit=limit,
        offset=offset,
    )
    return logs


# ==========================================================
# GET SPECIFIC AUCTION & BIDS HISTORY
# ==========================================================

@router.get(
    "/{auction_id}",
    response_model=AuctionResponse,
)
async def get_auction(
    auction_id: str,
    current_user: User = Depends(require_permission("auction:view")),
):
    auction_object_id = parse_object_id(
        auction_id,
        "auction ID",
    )

    auction = await Auction.get(
        auction_object_id
    )

    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auction not found",
        )

    return auction_to_response(auction)


@router.get(
    "/{auction_id}/bids",
    response_model=list[AuctionBidResponse],
)
async def get_auction_bids(
    auction_id: str,
    current_user: User = Depends(require_permission("auction:view")),
):
    auction_object_id = parse_object_id(
        auction_id,
        "auction ID",
    )

    auction = await Auction.get(
        auction_object_id
    )

    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auction not found",
        )

    bids = await AuctionBid.find(
        AuctionBid.auction_id == auction_object_id
    ).sort(
        AuctionBid.created_at
    ).to_list()

    return [
        AuctionBidResponse(
            id=str(bid.id),
            auction_id=str(bid.auction_id),
            team_id=str(bid.team_id),
            user_id=str(bid.user_id),
            amount=bid.amount,
            amount_display=maroon_to_pushp(bid.amount),
            created_at=bid.created_at,
        )
        for bid in bids
    ]


