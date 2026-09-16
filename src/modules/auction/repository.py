from beanie import PydanticObjectId

from src.modules.auction.model import Auction


class AuctionRepository:

    async def create(
            self,
            auction: Auction
    ) -> Auction:

        await auction.insert()
        return auction


    async def get_by_id(
            self,
            auction_id : PydanticObjectId
    ) -> Auction | None:

        return await Auction.get(auction_id)


    async def get_by_user(
            self,
            user_id : PydanticObjectId
    ) -> list[Auction]:

        return await Auction.find(
            Auction.user_id == user_id
        ).to_list()


    async def get_current(self) -> Auction | None:

        return await Auction.find_one(
            Auction.status == "live"
        )


    async def update(
            self,
            auction : Auction
    ) -> Auction:

        await auction.save()
        return auction