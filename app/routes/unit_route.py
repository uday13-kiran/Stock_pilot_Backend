from app.routes.crud_factory import build_crud_router
from app.models.units import Unit
from app.schemas.unit import UnitCreate, UnitResponse, UnitUpdate

router = build_crud_router(
    prefix="/units", tag="Units", model=Unit,
    create_schema=UnitCreate, response_schema=UnitResponse, update_schema=UnitUpdate,
    allow_delete=True, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"), write_roles=("admin",),
)
