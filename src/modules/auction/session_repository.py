from beanie import PydanticObjectId

from src.modules.auction.session_model import AuctionSession


class AuctionSessionRepository:

    async def create(
            self,
            session: AuctionSession,
    ) -> AuctionSession:

        await session.insert()
        return session

    async def get_by_id(
            self,
            session_id : PydanticObjectId
    ) -> AuctionSession | None:

        return await AuctionSession.get(session_id)


    async def get_current(self) -> AuctionSession | None:
        return await AuctionSession.find_one(
            {
                "status" : {
                    "$in" : ["live", "paused", "LIVE", "PAUSED"]
                }
            }
        )


    async def update(
            self,
            session: AuctionSession
    ) -> AuctionSession:

        await session.save()
        return session