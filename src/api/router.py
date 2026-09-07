from fastapi import APIRouter
from src.modules.auth.router import router as auth_router 
from src.modules.permission_groups.router import router as permission_group_router
from src.modules.permissions.router import router as permission_router
from src.modules.users.router import router as users_router
from src.modules.canteen.router import router as canteen_router
from src.modules.teams.router import router as team_router
from src.modules.app_config.router import router as app_config_router
from src.modules.sessions.router import router as sessions_router
from src.modules.registration.router import router as registration_router
from src.modules.team_assignments.router import router as team_assignments_router

router = APIRouter()


router.include_router(auth_router)
router.include_router(users_router)
router.include_router(permission_router)
router.include_router(permission_group_router)
router.include_router(canteen_router)
router.include_router(team_router)
router.include_router(app_config_router)
router.include_router(sessions_router)
router.include_router(registration_router)
router.include_router(team_assignments_router)