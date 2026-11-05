from app.routes.crud_factory import build_crud_router
from app.models.stock_transfer import StockTransfer
from app.schemas.stock_transfer import StockTransferCreate, StockTransferResponse, StockTransferUpdate

router = build_crud_router(
    prefix="/stock-transfers", tag="Stock Transfers", model=StockTransfer,
    create_schema=StockTransferCreate, response_schema=StockTransferResponse, update_schema=StockTransferUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "warehouse_staff"), write_roles=("inventory_manager", "warehouse_staff"),
)
