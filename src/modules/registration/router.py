from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import Response
from beanie import PydanticObjectId

from src.common.exceptions import NotFoundException
from src.common.utils import success_response
from src.modules.auth.dependencies import get_current_user, require_permission
from src.modules.registration.schema import RegistrationUpdate, RegistrationCreate
from src.modules.registration.service import RegistrationService
from src.modules.registration.repository import RegistrationRepository
from src.modules.users.model import User

router = APIRouter(
    prefix="/registration",
    tags=["Registration"]
)

repository = RegistrationRepository()
service = RegistrationService(repository)


@router.post("")
async def create_registration(
    data: RegistrationCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Complete participant registration questionnaire for current user.
    """
    registration = await service.create(
        user_id=current_user.id,
        data=data,
        current_user=current_user,
    )
    return success_response(
        code=201,
        message="Registration submitted successfully",
        data=service.format_registration(registration),
    )


@router.post("/import-csv")
async def import_registration_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(
        require_permission("registration:update")
    ),
):
    """Import questionnaire responses from CSV file (e.g. Google Forms / Excel)."""
    file_content = await file.read()
    result = await service.import_responses_from_csv(
        file_content,
        current_user_id=current_user.id,
    )

    return success_response(
        code=200,
        message=f"Import completed: {result['imported_count']} new, {result['updated_count']} updated, {len(result['duplicates'])} duplicate alerts, {len(result['unmatched'])} unmatched.",
        data=result,
    )


@router.get("/template")
async def download_registration_template(
    current_user: User = Depends(
        require_permission("registration:view")
    ),
):
    """Download CSV template for questionnaire responses import."""
    csv_header = (
        "email,roll_no,name,Which games do you play with enthusiasm?,"
        "How many years of experience do you have in the Bhaktiparv?,"
        "How do you respond in critical situation?,"
        "Creative Task & Talent,Sportsmanship,What do you prefer?\n"
        "rahul.sharma@bhaktiparv.com,CS202601,Rahul Kumar Sharma,Chess,More,\n"
        "\"Facing difficulty., I like taking responsibility in critical situation.\","
        "\"I have a creative talent/skill.\",\"I like to play with sportsman spirit.\",\"Teamwork.\"\n"
    )
    return Response(
        content=csv_header.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=registration_questionnaire_template.csv"},
    )


@router.get("/all")
async def get_all_registration(
    current_user: User = Depends(
        require_permission("registration:view")
    ),
):
    registrations = await service.get_all()
    return success_response(
        code=200,
        message="Registrations fetched successfully",
        data=[service.format_registration(r) for r in registrations],
    )


@router.get("")
async def get_all_registration_alias(
    current_user: User = Depends(
        require_permission("registration:view")
    ),
):
    registrations = await service.get_all()
    return success_response(
        code=200,
        message="Registrations fetched successfully",
        data=[service.format_registration(r) for r in registrations],
    )


@router.get("/user/{user_id}")
async def get_registration_by_user_id(
    user_id: PydanticObjectId,
    current_user: User = Depends(
        require_permission("registration:view")
    ),
):
    registration = await service.get_by_user_id(user_id)
    return success_response(
        code=200,
        message="Registration fetched successfully",
        data=service.format_registration(registration),
    )


@router.get("/{registration_id}")
async def get_registration(
    registration_id: PydanticObjectId,
    current_user: User = Depends(
        require_permission("registration:view")
    ),
):
    registration = await service.get_by_id(registration_id)
    return success_response(
        code=200,
        message="Registration fetched successfully",
        data=service.format_registration(registration),
    )


@router.put("/{registration_id}")
async def update_registration(
    registration_id: PydanticObjectId,
    data: RegistrationUpdate,
    current_user: User = Depends(
        require_permission("registration:update")
    ),
):
    registration = await service.update(
        registration_id,
        data,
        current_user,
    )
    return success_response(
        code=200,
        message="Registration updated successfully",
        data=service.format_registration(registration),
    )


@router.delete("/{registration_id}")
async def delete_registration(
    registration_id: PydanticObjectId,
    current_user: User = Depends(
        require_permission("registration:update")
    ),
):
    await service.delete(registration_id)
    return success_response(
        code=200,
        message="Registration removed successfully and user unregistered",
        data=None,
    )


@router.delete("/user/{user_id}")
async def unregister_user_by_id(
    user_id: PydanticObjectId,
    current_user: User = Depends(
        require_permission("registration:update")
    ),
):
    await service.delete_by_user_id(user_id)
    return success_response(
        code=200,
        message="User unregistered successfully",
        data=None,
    )