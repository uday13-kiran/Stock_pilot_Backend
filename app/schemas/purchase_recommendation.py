from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PurchaseRecommendationCreate(BaseModel):
    product_id: int
    warehouse_id: int | None = None
    suggested_quantity: int
    priority: str
    reason: str


class PurchaseRecommendationUpdate(BaseModel):
    priority: str | None = None
    reason: str | None = None


class PurchaseRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int | None
    suggested_quantity: int
    priority: str
    reason: str
    created_at: datetime
