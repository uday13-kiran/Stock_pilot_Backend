from app.routes.crud_factory import build_crud_router
from app.models.invoice_item import InvoiceItem
from app.schemas.invoice_item import InvoiceItemCreate, InvoiceItemResponse

router = build_crud_router(
    prefix="/invoice-items", tag="Invoice Items", model=InvoiceItem,
    create_schema=InvoiceItemCreate, response_schema=InvoiceItemResponse, 
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("sales_staff", "finance_billing_staff"), write_roles=("sales_staff", "finance_billing_staff"),
)
