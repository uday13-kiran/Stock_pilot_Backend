from app.routes.crud_factory import build_crud_router
from app.models.purchase_recommendation import PurchaseRecommendation
from app.schemas.purchase_recommendation import PurchaseRecommendationCreate, PurchaseRecommendationResponse, PurchaseRecommendationUpdate

router = build_crud_router(
    prefix="/purchase-recommendations", tag="Purchase Recommendations", model=PurchaseRecommendation,
    create_schema=PurchaseRecommendationCreate, response_schema=PurchaseRecommendationResponse, update_schema=PurchaseRecommendationUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "purchase_manager"), write_roles=("purchase_manager",),
)
