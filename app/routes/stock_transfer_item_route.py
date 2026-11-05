from app.routes.crud_factory import build_crud_router
from app.models.stock_transfer_item import StockTransferItem
from app.schemas.stock_transfer_item import StockTransferItemCreate, StockTransferItemResponse

router = build_crud_router(
    prefix="/stock-transfer-items", tag="Stock Transfer Items", model=StockTransferItem,
    create_schema=StockTransferItemCreate, response_schema=StockTransferItemResponse, 
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "warehouse_staff"), write_roles=("inventory_manager", "warehouse_staff"),
)
