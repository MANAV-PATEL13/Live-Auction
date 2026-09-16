import json
from typing import Any

from src.core.redis import redis_client
from src.modules.auction.constants import AuctionLiveKeys


class AuctionRedisService:

    async def set_current_auction(
        self,
        data: dict[str, Any],
    ) -> None:
        await redis_client.set(
            AuctionLiveKeys.CURRENT,
            json.dumps(data),
        )

    async def get_current_auction(
        self,
    ) -> dict[str, Any] | None:
        data = await redis_client.get(
            AuctionLiveKeys.CURRENT
        )

        if not data:
            return None

        return json.loads(data)

    async def clear_current_auction(self) -> None:
        await redis_client.delete(
            AuctionLiveKeys.CURRENT
        )

    async def set_status(
        self,
        status: str,
    ) -> None:
        await redis_client.set(
            AuctionLiveKeys.STATUS,
            status,
        )

    async def get_status(
        self,
    ) -> str | None:
        return await redis_client.get(
            AuctionLiveKeys.STATUS
        )

    async def set_bid(
        self,
        amount: int,
        team_id: str,
    ) -> None:
        await redis_client.set(
            AuctionLiveKeys.BID,
            json.dumps(
                {
                    "amount": amount,
                    "team_id": team_id,
                }
            ),
        )

    async def get_bid(
        self,
    ) -> dict[str, Any] | None:
        data = await redis_client.get(
            AuctionLiveKeys.BID
        )

        if not data:
            return None

        return json.loads(data)

    async def set_timer(
        self,
        seconds: int,
    ) -> None:
        await redis_client.set(
            AuctionLiveKeys.TIMER,
            seconds,
        )

    async def get_timer(self) -> int | None:
        value = await redis_client.get(
            AuctionLiveKeys.TIMER
        )

        if value is None:
            return None

        return int(value)

    async def set_bidding_enabled(
        self,
        enabled: bool,
    ) -> None:
        await redis_client.set(
            AuctionLiveKeys.BIDDING_ENABLED,
            "1" if enabled else "0",
        )

    async def is_bidding_enabled(self) -> bool:
        value = await redis_client.get(
            AuctionLiveKeys.BIDDING_ENABLED
        )

        if value is None:
            return True

        return value == "1"


    # QUEUE
    async def set_remaining_queue(
        self,
        user_ids: list[str],
    ) -> None:
        key = AuctionLiveKeys.REMAINING_QUEUE

        await redis_client.delete(key)

        if user_ids:
            await redis_client.rpush(
                key,
                *user_ids,
            )

    async def get_remaining_queue(
        self,
    ) -> list[str]:
        values = await redis_client.lrange(
            AuctionLiveKeys.REMAINING_QUEUE,
            0,
            -1,
        )

        return values

    async def pop_next_player(
        self,
    ) -> str | None:
        return await redis_client.lpop(
            AuctionLiveKeys.REMAINING_QUEUE
        )

    async def set_unsold_queue(
        self,
        user_ids: list[str],
    ) -> None:
        key = AuctionLiveKeys.UNSOLD_QUEUE

        await redis_client.delete(key)

        if user_ids:
            await redis_client.rpush(
                key,
                *user_ids,
            )

    async def get_unsold_queue(
        self,
    ) -> list[str]:
        values = await redis_client.lrange(
            AuctionLiveKeys.UNSOLD_QUEUE,
            0,
            -1,
        )

        return values

    async def push_unsold_player(
        self,
        user_id: str,
    ) -> None:
        await redis_client.rpush(
            AuctionLiveKeys.UNSOLD_QUEUE,
            user_id,
        )

    async def pop_unsold_player(
        self,
    ) -> str | None:
        return await redis_client.lpop(
            AuctionLiveKeys.UNSOLD_QUEUE
        )

    async def clear_queues(self) -> None:
        await redis_client.delete(
            AuctionLiveKeys.REMAINING_QUEUE,
            AuctionLiveKeys.UNSOLD_QUEUE,
        )

    async def set_session_id(
        self,
        session_id: str,
    ) -> None:
        await redis_client.set(
            AuctionLiveKeys.SESSION,
            session_id,
        )

    async def get_session_id(self) -> str | None:
        return await redis_client.get(
            AuctionLiveKeys.SESSION
        )

    async def clear_live_state(self) -> None:
        await redis_client.delete(
            AuctionLiveKeys.SESSION,
            AuctionLiveKeys.CURRENT,
            AuctionLiveKeys.STATUS,
            AuctionLiveKeys.BID,
            AuctionLiveKeys.TIMER,
            AuctionLiveKeys.REMAINING_QUEUE,
            AuctionLiveKeys.UNSOLD_QUEUE,
        )


    async def peek_next_player(self) -> str | None:
        return await redis_client.lindex(
            AuctionLiveKeys.REMAINING_QUEUE,
            0,
        )


auction_redis = AuctionRedisService()