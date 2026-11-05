from app.routes.crud_factory import build_crud_router
from app.models.warehouse_user import WarehouseUser
from app.schemas.warehouse_user import WarehouseUserCreate, WarehouseUserResponse

router = build_crud_router(
    prefix="/warehouse-users", tag="Warehouse Users", model=WarehouseUser,
    create_schema=WarehouseUserCreate, response_schema=WarehouseUserResponse, 
    allow_delete=True, immutable=False, field_aliases={},
)
