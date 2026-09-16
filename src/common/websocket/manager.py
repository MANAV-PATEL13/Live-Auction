from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self.public_connections: set[WebSocket] = set()
        self.admin_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, client_type: str = "public") -> None:
        await websocket.accept()
        self.connections.add(websocket)
        if client_type == "public":
            self.public_connections.add(websocket)
        else:
            self.admin_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)
        self.public_connections.discard(websocket)
        self.admin_connections.discard(websocket)

    @property
    def public_connection_count(self) -> int:
        return len(self.public_connections)

    @property
    def connection_count(self) -> int:
        # Public spectators / joined viewers count only
        return len(self.public_connections)

    async def send_personal(
        self,
        websocket: WebSocket,
        message: dict[str, Any],
    ) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def broadcast(
        self,
        message: dict[str, Any],
    ) -> None:
        disconnected: list[WebSocket] = []

        for websocket in list(self.connections):
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)


websocket_manager = WebSocketManager()