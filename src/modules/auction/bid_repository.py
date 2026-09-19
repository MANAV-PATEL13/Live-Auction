from beanie import PydanticObjectId

from src.modules.auction.bid_model import AuctionBid


class AuctionBidRepository:

    async def create(
            self,
            bid : AuctionBid
    ) -> AuctionBid:

        await bid.insert()
        return bid


    async def get_by_id(
            self,
            bid_id : PydanticObjectId
    ) -> AuctionBid | None:
 
        return await AuctionBid.get(bid_id)


    async def get_by_auction(
            self,
            auction_id : PydanticObjectId
    ) -> list[AuctionBid]:

        return await AuctionBid.find(
            AuctionBid.auction_id == auction_id
        ).sort(
            AuctionBid.created_at
        ).to_list()


    async def get_latest(
            self,
            auction_id : PydanticObjectId
    ) -> AuctionBid | None:

        bids = await self.get_by_auction(auction_id)

        if not bids:
            return None

        return bids[-1]

    