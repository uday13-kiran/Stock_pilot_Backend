from app.routes.crud_factory import build_crud_router
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceUpdate

router = build_crud_router(
    prefix="/invoices", tag="Invoices", model=Invoice,
    create_schema=InvoiceCreate, response_schema=InvoiceResponse, update_schema=InvoiceUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("sales_staff", "finance_billing_staff"), write_roles=("sales_staff", "finance_billing_staff"),
)
