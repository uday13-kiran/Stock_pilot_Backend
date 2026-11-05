from app.routes.crud_factory import build_crud_router
from app.models.sales_return import SalesReturn
from app.schemas.sales_return import SalesReturnCreate, SalesReturnResponse, SalesReturnUpdate

router = build_crud_router(
    prefix="/sales-returns", tag="Sales Returns", model=SalesReturn,
    create_schema=SalesReturnCreate, response_schema=SalesReturnResponse, update_schema=SalesReturnUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("sales_staff", "finance_billing_staff"), write_roles=("sales_staff", "finance_billing_staff"),
)
