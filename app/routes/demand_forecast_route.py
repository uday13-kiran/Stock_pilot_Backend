from app.routes.crud_factory import build_crud_router
from app.models.demand_forecast import DemandForecast
from app.schemas.demand_forecast import DemandForecastCreate, DemandForecastResponse

router = build_crud_router(
    prefix="/demand-forecasts", tag="Demand Forecasts", model=DemandForecast,
    create_schema=DemandForecastCreate, response_schema=DemandForecastResponse, 
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "purchase_manager"), write_roles=("admin",),
)
