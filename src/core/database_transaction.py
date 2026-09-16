from contextlib import asynccontextmanager

from src.core.database import client


@asynccontextmanager
async def mongo_transaction():
    async with client.start_session() as session:
        await session.start_transaction()

        try:
            yield session
        except Exception:
            await session.abort_transaction()
            raise
        else:
            await session.commit_transaction()