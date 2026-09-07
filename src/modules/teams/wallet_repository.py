from beanie import PydanticObjectId
from src.modules.teams.wallet_model import TeamWalletTransaction


class TeamWalletRepository:

    async def create(
        self,
        transaction: TeamWalletTransaction,
    ) -> TeamWalletTransaction:
        await transaction.insert()
        return transaction

    async def get_by_team(
        self,
        team_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TeamWalletTransaction]:
        return (
            await TeamWalletTransaction.find(
                TeamWalletTransaction.team_id == team_id
            )
            .sort(-TeamWalletTransaction.created_at)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def count_by_team(
        self,
        team_id: PydanticObjectId,
    ) -> int:
        return await TeamWalletTransaction.find(
            TeamWalletTransaction.team_id == team_id
        ).count()

    async def get_by_user(
        self,
        user_id: PydanticObjectId,
    ) -> list[TeamWalletTransaction]:
        return (
            await TeamWalletTransaction.find(
                TeamWalletTransaction.user_id == user_id
            )
            .sort(-TeamWalletTransaction.created_at)
            .to_list()
        )
