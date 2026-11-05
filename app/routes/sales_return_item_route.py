from app.routes.crud_factory import build_crud_router
from app.models.sales_return_item import SalesReturnItem
from app.schemas.sales_return_item import SalesReturnItemCreate, SalesReturnItemResponse

router = build_crud_router(
    prefix="/sales-return-items", tag="Sales Return Items", model=SalesReturnItem,
    create_schema=SalesReturnItemCreate, response_schema=SalesReturnItemResponse, 
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("sales_staff", "finance_billing_staff"), write_roles=("sales_staff", "finance_billing_staff"),
)
