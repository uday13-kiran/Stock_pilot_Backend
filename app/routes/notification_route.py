from app.routes.crud_factory import build_crud_router
from app.models.notifications import Notification
from app.schemas.notification import NotificationCreate, NotificationResponse, NotificationUpdate

router = build_crud_router(
    prefix="/notifications", tag="Notifications", model=Notification,
    create_schema=NotificationCreate, response_schema=NotificationResponse, update_schema=NotificationUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"), write_roles=("admin",),
)
