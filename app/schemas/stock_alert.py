from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockAlertCreate(BaseModel):
    product_id: int
    warehouse_id: int
    current_stock: int
    reorder_level: int
    severity: str
    alert_type: str
    is_resolved: bool = False


class StockAlertUpdate(BaseModel):
    is_resolved: bool | None = None
    severity: str | None = None


class StockAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    current_stock: int
    reorder_level: int
    severity: str
    alert_type: str
    is_resolved: bool
    created_at: datetime
