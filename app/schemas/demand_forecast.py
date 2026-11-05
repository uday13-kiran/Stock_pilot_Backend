from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DemandForecastCreate(BaseModel):
    product_id: int
    warehouse_id: int | None = None
    forecast_period: str
    predicted_demand: float
    forecast_method: str | None = None


class DemandForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int | None
    forecast_period: str
    predicted_demand: float
    forecast_method: str | None
    created_at: datetime
