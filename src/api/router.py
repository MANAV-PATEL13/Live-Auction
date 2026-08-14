from fastapi import APIRouter
from src.modules.auth.router import router as auth_router 
from src.modules.permission_groups.router import router as permission_group_router
from src.modules.permissions.router import router as permission_router
from src.modules.permission_groups.router import router as permission_group_router


router = APIRouter()


router.include_router(auth_router)
router.include_router(permission_router)
router.include_router(permission_group_router)
router.include_router(permission_group_router)

