from app.routes.crud_factory import build_crud_router
from app.models.stock_adjusment import StockAdjustment
from app.schemas.stock_adjustment import StockAdjustmentCreate, StockAdjustmentResponse, StockAdjustmentUpdate

router = build_crud_router(
    prefix="/stock-adjustments", tag="Stock Adjustments", model=StockAdjustment,
    create_schema=StockAdjustmentCreate, response_schema=StockAdjustmentResponse, update_schema=StockAdjustmentUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("inventory_manager",), write_roles=("inventory_manager",),
)
