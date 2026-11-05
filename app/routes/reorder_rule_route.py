from app.routes.crud_factory import build_crud_router
from app.models.reorder_rule import ReorderRule
from app.schemas.reorder_rule import ReorderRuleCreate, ReorderRuleResponse, ReorderRuleUpdate

router = build_crud_router(
    prefix="/reorder-rules", tag="Reorder Rules", model=ReorderRule,
    create_schema=ReorderRuleCreate, response_schema=ReorderRuleResponse, update_schema=ReorderRuleUpdate,
    allow_delete=True, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "purchase_manager"), write_roles=("inventory_manager",),
)
