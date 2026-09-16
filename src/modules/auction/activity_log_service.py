import json
from datetime import datetime, timezone
from typing import Any
from beanie import PydanticObjectId
from src.core.redis import redis_client
from src.modules.auction.activity_log_model import AuctionActivityLog
from src.common.websocket.websocket import auction_websocket, AuctionWebSocketEvent

REDIS_ACTIVITY_LOGS_KEY = "auction:activity_logs"
MAX_REDIS_LOGS = 250


class AuctionActivityLogService:

    async def log_activity(
        self,
        type: str,
        title: str,
        description: str,
        session_id: PydanticObjectId | None = None,
        auction_id: PydanticObjectId | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        now_dt = datetime.now(timezone.utc)
        log_payload = {
            "type": type,
            "title": title,
            "description": description,
            "session_id": str(session_id) if session_id else None,
            "auction_id": str(auction_id) if auction_id else None,
            "metadata": metadata or {},
            "created_at": now_dt.isoformat(),
        }

        # 1. Insert into Permanent MongoDB Database
        try:
            log_entry = AuctionActivityLog(
                session_id=session_id,
                auction_id=auction_id,
                type=type,
                title=title,
                description=description,
                metadata=metadata or {},
                created_at=now_dt,
            )
            await log_entry.insert()
            log_payload["id"] = str(log_entry.id)
        except Exception as e:
            print(f"[ActivityLog] Error writing to MongoDB: {e}")
            log_payload["id"] = f"redis-{now_dt.timestamp()}"

        # 2. Store in Redis Fast List (Capped at 250 items)
        try:
            await redis_client.lpush(
                REDIS_ACTIVITY_LOGS_KEY,
                json.dumps(log_payload),
            )
            await redis_client.ltrim(
                REDIS_ACTIVITY_LOGS_KEY,
                0,
                MAX_REDIS_LOGS - 1,
            )
        except Exception as e:
            print(f"[ActivityLog] Error writing to Redis: {e}")

        # 3. Broadcast Real-time WebSocket Event
        try:
            await auction_websocket.broadcast(
                AuctionWebSocketEvent.ACTIVITY_LOG,
                log_payload,
            )
        except Exception as e:
            print(f"[ActivityLog] Error broadcasting WebSocket: {e}")

        return log_payload

    async def get_logs(
        self,
        session_id: PydanticObjectId | None = None,
        type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        # 1. Try fetching from MongoDB first
        try:
            query = {}
            if session_id:
                query["session_id"] = session_id
            if type and type != "ALL":
                query["type"] = type

            mongo_logs = (
                await AuctionActivityLog.find(query)
                .sort("-created_at")
                .skip(offset)
                .limit(limit)
                .to_list()
            )

            if mongo_logs:
                return [
                    {
                        "id": str(log.id),
                        "type": log.type,
                        "title": log.title,
                        "description": log.description,
                        "session_id": str(log.session_id) if log.session_id else None,
                        "auction_id": str(log.auction_id) if log.auction_id else None,
                        "metadata": log.metadata,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    }
                    for log in mongo_logs
                ]
        except Exception as e:
            print(f"[ActivityLog] MongoDB fetch error, falling back to Redis: {e}")

        # 2. Fallback to Redis Cache
        try:
            raw_items = await redis_client.lrange(
                REDIS_ACTIVITY_LOGS_KEY,
                offset,
                offset + limit - 1,
            )
            parsed_logs = []
            for item in raw_items:
                try:
                    data = json.loads(item)
                    if type and type != "ALL" and data.get("type") != type:
                        continue
                    if session_id and data.get("session_id") != str(session_id):
                        continue
                    parsed_logs.append(data)
                except Exception:
                    continue
            return parsed_logs
        except Exception as e:
            print(f"[ActivityLog] Redis fetch error: {e}")
            return []


auction_activity_service = AuctionActivityLogService()

