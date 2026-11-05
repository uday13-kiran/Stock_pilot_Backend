from app.routes.crud_factory import build_crud_router
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseResponse, WarehouseUpdate

router = build_crud_router(
    prefix="/warehouses", tag="Warehouses", model=Warehouse,
    create_schema=WarehouseCreate, response_schema=WarehouseResponse, update_schema=WarehouseUpdate,
    allow_delete=True, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "purchase_manager", "warehouse_staff"), write_roles=("admin",),
)
