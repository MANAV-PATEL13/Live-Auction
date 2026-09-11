from datetime import datetime, timezone
from enum import Enum
from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


from src.modules.teams.wallet_constants import WalletTransactionType

TransactionType = WalletTransactionType


class TeamWalletTransaction(Document):
    team_id: PydanticObjectId
    transaction_type: WalletTransactionType
    amount: int
    balance_before: int
    balance_after: int
    user_id: PydanticObjectId | None = None
    description: str | None = None
    reference_id: str | None = None
    created_by: PydanticObjectId | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "team_wallet_transactions"

        indexes = [
            IndexModel(
                [("team_id", ASCENDING), ("created_at", DESCENDING)],
                name="idx_wallet_team_created",
            ),
            IndexModel(
                [("user_id", ASCENDING)],
                name="idx_wallet_user",
            ),
            IndexModel(
                [("transaction_type", ASCENDING)],
                name="idx_wallet_tx_type",
            ),
        ]
