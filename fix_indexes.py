import asyncio
import os
from pymongo import AsyncMongoClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DATABASE_NAME", "bhaktipurv")
    client = AsyncMongoClient(url)

    # Try to get config from settings
    try:
        from src.core.config import settings
        url = settings.MONGO_URL
        db_name = settings.DATABASE_NAME
        client = AsyncMongoClient(url)
        print(f"Using settings: db={db_name}")
    except Exception as e:
        print(f"Could not load settings ({e}), using env vars: db={db_name}")

    db = client[db_name]
    coll = db["sessions"]

    indexes = await coll.index_information()
    print("Current indexes on 'sessions':")
    for name, info in indexes.items():
        print(f"  {name}: {info.get('key')}")

    # Drop any auto-generated index that conflicts with our named ones
    # (any index not starting with "idx_" and not the default _id_)
    to_drop = [
        name for name in indexes
        if name != "_id_" and not name.startswith("idx_")
    ]

    if to_drop:
        for name in to_drop:
            print(f"Dropping conflicting index: {name}")
            await coll.drop_index(name)
        print("Done. Restart the server now.")
    else:
        print("No conflicting indexes found.")

asyncio.run(main())
