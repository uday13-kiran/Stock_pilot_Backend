from app.routes.crud_factory import build_crud_router
from app.models.sales import Sale
from app.schemas.sale import SaleCreate, SaleResponse, SaleUpdate

router = build_crud_router(
    prefix="/sales", tag="Sales", model=Sale,
    create_schema=SaleCreate, response_schema=SaleResponse, update_schema=SaleUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("sales_staff", "finance_billing_staff"), write_roles=("sales_staff",),
)
