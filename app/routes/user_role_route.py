from app.routes.crud_factory import build_crud_router
from app.models.user_role import UserRole
from app.schemas.user_role import UserRoleCreate, UserRoleResponse

router = build_crud_router(
    prefix="/user-roles", tag="User Roles", model=UserRole,
    create_schema=UserRoleCreate, response_schema=UserRoleResponse, 
    allow_delete=True, immutable=False, field_aliases={},
)
