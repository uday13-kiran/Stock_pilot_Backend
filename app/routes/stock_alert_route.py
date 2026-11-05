from app.routes.crud_factory import build_crud_router
from app.models.stock_alert import StockAlert
from app.schemas.stock_alert import StockAlertCreate, StockAlertResponse, StockAlertUpdate

router = build_crud_router(
    prefix="/stock-alerts", tag="Stock Alerts", model=StockAlert,
    create_schema=StockAlertCreate, response_schema=StockAlertResponse, update_schema=StockAlertUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "warehouse_staff"), write_roles=("admin",),
)
