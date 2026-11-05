from app.routes.crud_factory import build_crud_router
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate

router = build_crud_router(
    prefix="/customers", tag="Customers", model=Customer,
    create_schema=CustomerCreate, response_schema=CustomerResponse, update_schema=CustomerUpdate,
    allow_delete=True, immutable=False, field_aliases={},
    read_roles=("sales_staff", "finance_billing_staff"), write_roles=("sales_staff",),
)
