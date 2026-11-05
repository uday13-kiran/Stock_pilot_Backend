from app.routes.crud_factory import build_crud_router
from app.models.supplier_products import SupplierProduct
from app.schemas.supplier_product import SupplierProductCreate, SupplierProductResponse

router = build_crud_router(
    prefix="/supplier-products", tag="Supplier Products", model=SupplierProduct,
    create_schema=SupplierProductCreate, response_schema=SupplierProductResponse, 
    allow_delete=True, immutable=False, field_aliases={},
    read_roles=("purchase_manager",), write_roles=("purchase_manager",),
)
