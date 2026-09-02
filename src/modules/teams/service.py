from beanie import PydanticObjectId

from src.modules.teams.model import Team
from src.modules.teams.schema import TeamCreate, TeamUpdate
from src.modules.teams.repository import TeamRepository
from src.modules.users.model import User
from src.modules.users.repository import UserRepository

from src.common.exceptions import(
    ConflictException,
    NotFoundException
)

class TeamService:

    def __init__(
            self,
            repository : TeamRepository,
            user_repository : UserRepository,
        ):

        self.repository = repository
        self.user_repository = user_repository

    # Helpers
    @staticmethod
    def _normalize_name(value : str) -> str:
        return value.strip()

    @staticmethod
    def _normalize_code(value : str) -> str:
        return value.strip().upper()



    # validate user is existing
    async def _validate_user(
            self,
            user_id : str | None,
    ) -> PydanticObjectId | None:

        if not user_id:
            return None

        if not PydanticObjectId.is_valid(user_id):
            raise NotFoundException(
                "User not found"
            )

        object_id = PydanticObjectId(user_id)

        user = await self.user_repository.get_by_id(
            object_id
        )

        if not user:
            raise NotFoundException(
                "User not found"
            )

        return object_id



    async def create(
            self,
            data : TeamCreate,
            current_user : User
    ) -> Team:

        name = self._normalize_name(data.name)
        code = self._normalize_name(data.code)

        existing = await self.repository.get_by_code(code)

        if existing:
            raise ConflictException(
                f"Team with code '{code}' already exists"
            )

        captain_id = await self._validate_user(
            data.captain_id
        )

        
        vice_captain_id = await self._validate_user(
            data.vice_captain_id
        )

        if captain_id and vice_captain_id and captain_id == vice_captain_id:
            raise ConflictException(
                "Captain and vice-captain cannot be the same user"
            )
        

        team = Team(
            name=name,
            code =code,

            image_url=data.image_url,

            captain_id=captain_id,
            vice_captain_id=vice_captain_id,
            is_active=data.is_active,
            created_by=current_user.id,
            updated_by=current_user.id,
        )

        return await self.repository.create(team)

    async def get_by_id(
            self,
            team_id : PydanticObjectId
    ) -> Team:

        team = await self.repository.get_by_id(team_id)

        if not team:
            raise NotFoundException("Team not found")

        return team

    async def get_all(
            self,
            active_only : bool = False,
    ) -> list[Team]:

        return await self.repository.get_all(
            active_only=active_only
        )

    async def update(
        self,
        team_id: PydanticObjectId,
        data: TeamUpdate,
        current_user: User,
    ) -> Team:

        team = await self.get_by_id(team_id)

        update_data = data.model_dump(
            exclude_unset=True
        )

        if "name" in update_data:
            update_data["name"] = self._normalize_name(
                update_data["name"]
            )

        # If code is being changed, check duplicate
        if "code" in update_data:

            update_data["code"] = self._normalize_code(
                update_data["code"]
            )

            existing = await self.repository.get_by_code(
                update_data["code"]
            )

            if existing and existing.id != team.id:
                raise ConflictException(
                    f"Team with code '{update_data['code']}' already exists"
                )

        # validate caption
        if "captain_id" in update_data:
            update_data["captain_id"] = (
                await self._validate_user(
                    update_data["captain_id"]
                )
            )

        # validate vice_caption
        if "vice_captain_id" in update_data:
            update_data["vice_captain_id"] = (
                await self._validate_user(
                    update_data["vice_captain_id"]
                )
            )

        captain_id = update_data.get(
            "captain_id",
            team.captain_id,
        )

        vice_captain_id = update_data.get(
            "vice_captain_id",
            team.vice_captain_id,
        )

        if captain_id and vice_captain_id and captain_id == vice_captain_id:
            raise ConflictException(
                "Captain and vice-captain cannot be the same user"
            )
        

        for field, value in update_data.items():
            setattr(
                team,
                field,
                value
            )

        team.mark_updated(current_user.id)

        return await self.repository.update(team)

    async def deactivate(
        self,
        team_id: PydanticObjectId,
        current_user : User,
    ) -> Team:

        team = await self.get_by_id(team_id)

        if not team.is_active:
            return team

        team.is_active = False

        team.mark_updated(
            current_user.id
        )

        return await self.repository.update(
            team
        )