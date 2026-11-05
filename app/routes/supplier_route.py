from app.routes.crud_factory import build_crud_router
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate

router = build_crud_router(
    prefix="/suppliers", tag="Suppliers", model=Supplier,
    create_schema=SupplierCreate, response_schema=SupplierResponse, update_schema=SupplierUpdate,
    allow_delete=True, immutable=False, field_aliases={},
    read_roles=("purchase_manager", "inventory_manager"), write_roles=("purchase_manager",),
)
