import asyncio

from src.core.database import init_database
from src.modules.permissions.model import Permission

ALL_PERMISSIONS = [
    {"name": "Create User", "code": "user:create", "description": "Permission to create new user accounts"},
    {"name": "View User", "code": "user:view", "description": "Permission to view user profiles and listings"},
    {"name": "Update User", "code": "user:update", "description": "Permission to modify user details and permissions"},
    {"name": "Delete User", "code": "user:delete", "description": "Permission to delete user accounts"},
    {"name": "Create Permission", "code": "permission:create", "description": "Permission to define new system permissions"},
    {"name": "View Permission", "code": "permission:view", "description": "Permission to view permissions catalog"},
    {"name": "Update Permission", "code": "permission:update", "description": "Permission to modify system permissions"},
    {"name": "Delete Permission", "code": "permission:delete", "description": "Permission to delete system permissions"},
    {"name": "Create Permission Group", "code": "permission_group:create", "description": "Permission to create role permission groups"},
    {"name": "View Permission Group", "code": "permission_group:view", "description": "Permission to view role permission groups"},
    {"name": "Update Permission Group", "code": "permission_group:update", "description": "Permission to update role permission groups"},
    {"name": "Delete Permission Group", "code": "permission_group:delete", "description": "Permission to delete role permission groups"},
    {"name": "User Access", "code": "user:access", "description": "Permission to toggle user access and account activation"},
    {"name": "Create Canteen Item", "code": "canteen:item:create", "description": "Permission to create canteen menu items"},
    {"name": "View Canteen Item", "code": "canteen:item:view", "description": "Permission to view canteen menu items"},
    {"name": "Update Canteen Item", "code": "canteen:item:update", "description": "Permission to update canteen menu items"},
    {"name": "Delete Canteen Item", "code": "canteen:item:delete", "description": "Permission to delete canteen menu items"},
    {"name": "Create Team", "code": "team:create", "description": "Permission to create new teams"},
    {"name": "Update Team", "code": "team:update", "description": "Permission to update team metadata and balance"},
    {"name": "View Team", "code": "team:view", "description": "Permission to view teams and rosters"},
    {"name": "View All Teams", "code": "team:viewall", "description": "Permission to view all teams across the system"},
    {"name": "Delete Team", "code": "team:delete", "description": "Permission to delete teams"},
    {"name": "AppConfig View", "code": "appconfig:view", "description": "Permission to view application system settings"},
    {"name": "AppConfig Update", "code": "appconfig:update", "description": "Permission to modify application system settings"},
    {"name": "Session history View", "code": "sessions:view", "description": "Permission to view active and past user device sessions"},
    {"name": "Registration View", "code": "registration:view", "description": "Permission to view participant registrations and responses"},
    {"name": "Registration Update", "code": "registration:update", "description": "Permission to update, import, or manage registrations"},
    {"name": "Assign Team", "code": "team:assign", "description": "Permission to manually assign, transfer, or remove players from teams"},
    {"name": "Auction start", "code": "auction:start", "description": "Permission to initialize and start live auction sessions"},
    {"name": "Auction Pause", "code": "auction:pause", "description": "Permission to pause and resume active auction sessions"},
    {"name": "Auction End", "code": "auction:end", "description": "Permission to officially end auction sessions"},
    {"name": "Auction Sell", "code": "auction:sell", "description": "Permission to award and sell current player to winning team"},
    {"name": "Auction Rollback", "code": "auction:rollback", "description": "Permission to rollback bids or sold auction outcomes"},
    {"name": "Auction Update", "code": "auction:update", "description": "Permission to update player queue, bidding state, and quick add players"},
    {"name": "Auction View", "code": "auction:view", "description": "Permission to view live auction control screens and floor state"},
]


async def seed_permissions():
    await init_database()

    created_count = 0
    updated_count = 0

    for item in ALL_PERMISSIONS:
        existing = await Permission.find_one(Permission.code == item["code"])
        if existing:
            existing.name = item["name"]
            existing.description = item["description"]
            existing.is_active = True
            await existing.save()
            updated_count += 1
        else:
            new_perm = Permission(
                name=item["name"],
                code=item["code"],
                description=item["description"],
                is_active=True,
            )
            await new_perm.insert()
            created_count += 1

    print(f"Permissions seeding finished: {created_count} created, {updated_count} updated. Total: {len(ALL_PERMISSIONS)}")


if __name__ == "__main__":
    asyncio.run(seed_permissions())
