from app.routes.crud_factory import build_crud_router
from app.models.brands import Brand
from app.schemas.brand import BrandCreate, BrandResponse, BrandUpdate

router = build_crud_router(
    prefix="/brands", tag="Brands", model=Brand,
    create_schema=BrandCreate, response_schema=BrandResponse, update_schema=BrandUpdate,
    allow_delete=True, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"), write_roles=("admin",),
)
