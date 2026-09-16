import asyncio
import io
import httpx
from src.core.database import init_database
from src.modules.users.model import User
from src.core.jwt import create_access_token

async def test_live():
    await init_database()
    user = await User.find_one(User.is_superuser == True)
    if not user:
        user = await User.find_one()
    print("Testing with user:", user.email)
    token = create_access_token(str(user.id), "test_session_id")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:3000") as client:
        # 1. Test Permissions import
        f1 = {"file": ("permissions.csv", io.BytesIO(b"name,code,description,is_active\nTest Perm,test:perm_code,Test capability,true\n"), "text/csv")}
        res1 = await client.post("/permissions/import", headers=headers, files=f1)
        print("Permissions Import Response:", res1.status_code, res1.json())
        
        # 2. Test Permission Groups import
        f2 = {"file": ("groups.csv", io.BytesIO(b"name,description,permissions,is_active\nTest Role Group,Sample desc,test:perm_code;user:view,true\n"), "text/csv")}
        res2 = await client.post("/permission-groups/import", headers=headers, files=f2)
        print("Permission Groups Import Response:", res2.status_code, res2.json())

if __name__ == "__main__":
    asyncio.run(test_live())
