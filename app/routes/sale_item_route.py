from app.routes.crud_factory import build_crud_router
from app.models.sales_item import SaleItem
from app.schemas.sale_item import SaleItemCreate, SaleItemResponse

router = build_crud_router(
    prefix="/sale-items", tag="Sale Items", model=SaleItem,
    create_schema=SaleItemCreate, response_schema=SaleItemResponse, 
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("sales_staff", "finance_billing_staff"), write_roles=("sales_staff",),
)
