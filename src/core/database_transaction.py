from contextlib import asynccontextmanager
from src.core.database import client

@asynccontextmanager
async def mongo_transaction():
    async with client.start_session() as session:
        async with session.start_transaction():
            yield session
