from typing import Any

from src.common.websocket.manager import websocket_manager


class AuctionWebSocketEvent:
    SESSION_STARTED = "auction:session_started"
    PLAYER_STARTED = "auction:player_started"
    BID = "auction:bid"
    BID_ROLLBACK = "auction:bid_rollback"
    PLAYER_SOLD = "auction:player_sold"
    PLAYER_UNSOLD = "auction:player_unsold"
    PAUSED = "auction:paused"
    RESUMED = "auction:resumed"
    ENDED = "auction:ended"
    STATE = "auction:state"
    VIEWER_COUNT = "auction:viewer_count"
    BIDDING_TOGGLED = "auction:bidding_toggled"
    ACTIVITY_LOG = "auction:activity_log"


class AuctionWebSocketService:

    async def broadcast(
        self,
        event: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        await websocket_manager.broadcast(
            {
                "event": event,
                "data": data or {},
            }
        )

    async def send_state(
        self,
        state: dict[str, Any],
    ) -> None:
        await self.broadcast(
            AuctionWebSocketEvent.STATE,
            state,
        )


auction_websocket = AuctionWebSocketService()