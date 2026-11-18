from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import app.models  # noqa: F401 - register all ORM models
from app.core.database import Base, engine
from app.core.config import settings
from app.routes.category_route import router as category_router
from app.routes.products_routes import router as product_router
from app.routes.inventory_route import router as inventory_router
from app.routes.auth_route import router as auth_router
from app.routes.user_route import router as user_router
from app.routes.role_route import router as role_router
from app.routes.brand_route import router as brand_router
from app.routes.customer_route import router as customer_router
from app.routes.supplier_route import router as supplier_router
from app.routes.warehouse_route import router as warehouse_router
from app.routes.unit_route import router as unit_router
from app.routes.purchase_order_route import router as purchase_order_router
from app.routes.purchase_order_item_route import router as purchase_order_item_router
from app.routes.goods_receipt_route import router as goods_receipt_router
from app.routes.goods_receipt_item_route import router as goods_receipt_item_router
from app.routes.sale_route import router as sale_router
from app.routes.sale_item_route import router as sale_item_router
from app.routes.invoice_route import router as invoice_router
from app.routes.invoice_item_route import router as invoice_item_router
from app.routes.payment_route import router as payment_router
from app.routes.stock_transfer_route import router as stock_transfer_router
from app.routes.stock_transfer_item_route import router as stock_transfer_item_router
from app.routes.sales_return_route import router as sales_return_router
from app.routes.sales_return_item_route import router as sales_return_item_router
from app.routes.stock_adjustment_route import router as stock_adjustment_router
from app.routes.reorder_rule_route import router as reorder_rule_router
from app.routes.demand_forecast_route import router as demand_forecast_router
from app.routes.purchase_recommendation_route import router as purchase_recommendation_router
from app.routes.stock_alert_route import router as stock_alert_router
from app.routes.notification_route import router as notification_router
from app.routes.low_stock_notification_route import router as low_stock_notification_router
from app.routes.audit_log_route import router as audit_log_router
from app.routes.supplier_product_route import router as supplier_product_router
from app.routes.warehouse_user_route import router as warehouse_user_router
from app.routes.inventory_movement_route import router as inventory_movement_router
from app.routes.reports_route import router as reports_router
from app.routes.workflow_route import router as workflow_router
from app.routes.planning_route import router as planning_router
from app.routes.assistant_route import router as assistant_router
from app.core.dependencies import get_current_user, require_roles
from fastapi import Depends

@asynccontextmanager
async def lifespan(application: FastAPI):
    # Convenience only for local development. Production should use Alembic migrations.
    if settings.environment.lower() == "development":
        Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=settings.app_name, version="1.0.0", debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Route-level access is enforced by database-assigned roles. Admin bypasses all business
# role lists through require_roles(); identity administration remains admin-only.
def include_for_roles(api_router, roles):
    app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(require_roles(*roles))])


app.include_router(auth_router, prefix="/api/v1")

# Read access is broad enough for each role's workflow; write access is narrowed inside
# custom routes or by build_crud_router's read_roles/write_roles policy.
include_for_roles(category_router, ("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"))
include_for_roles(product_router, ("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"))
include_for_roles(inventory_router, ("inventory_manager", "warehouse_staff", "sales_staff"))
include_for_roles(brand_router, ("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"))
include_for_roles(unit_router, ("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"))
include_for_roles(customer_router, ("sales_staff", "finance_billing_staff"))
include_for_roles(supplier_router, ("purchase_manager", "inventory_manager"))
include_for_roles(warehouse_router, ("inventory_manager", "purchase_manager", "warehouse_staff"))
include_for_roles(purchase_order_router, ("purchase_manager", "inventory_manager"))
include_for_roles(purchase_order_item_router, ("purchase_manager", "inventory_manager"))
include_for_roles(goods_receipt_router, ("purchase_manager", "inventory_manager", "warehouse_staff"))
include_for_roles(goods_receipt_item_router, ("purchase_manager", "inventory_manager", "warehouse_staff"))
include_for_roles(sale_router, ("sales_staff", "finance_billing_staff"))
include_for_roles(sale_item_router, ("sales_staff", "finance_billing_staff"))
include_for_roles(invoice_router, ("sales_staff", "finance_billing_staff"))
include_for_roles(invoice_item_router, ("sales_staff", "finance_billing_staff"))
include_for_roles(payment_router, ("finance_billing_staff",))
include_for_roles(stock_transfer_router, ("inventory_manager", "warehouse_staff"))
include_for_roles(stock_transfer_item_router, ("inventory_manager", "warehouse_staff"))
include_for_roles(sales_return_router, ("sales_staff", "finance_billing_staff"))
include_for_roles(sales_return_item_router, ("sales_staff", "finance_billing_staff"))
include_for_roles(stock_adjustment_router, ("inventory_manager",))
include_for_roles(reorder_rule_router, ("inventory_manager", "purchase_manager"))
include_for_roles(demand_forecast_router, ("inventory_manager", "purchase_manager"))
include_for_roles(purchase_recommendation_router, ("inventory_manager", "purchase_manager"))
include_for_roles(stock_alert_router, ("inventory_manager", "warehouse_staff"))
include_for_roles(
    low_stock_notification_router,
    ("inventory_manager", "purchase_manager", "warehouse_staff", "sales_staff", "finance_billing_staff"),
)
include_for_roles(notification_router, ("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"))
include_for_roles(audit_log_router, ("admin",))
include_for_roles(supplier_product_router, ("purchase_manager",))
include_for_roles(inventory_movement_router, ("inventory_manager", "warehouse_staff"))
include_for_roles(reports_router, ("inventory_manager", "purchase_manager", "warehouse_staff", "finance_billing_staff"))
include_for_roles(workflow_router, ("inventory_manager", "purchase_manager", "sales_staff", "warehouse_staff", "finance_billing_staff"))
include_for_roles(planning_router, ("inventory_manager", "purchase_manager"))
include_for_roles(
    assistant_router,
    ("inventory_manager", "purchase_manager", "sales_staff", "finance_billing_staff"),
)

# User, role, role-assignment, and warehouse-user administration are Admin-only.
for admin_router in (user_router, role_router, warehouse_user_router):
    app.include_router(admin_router, prefix="/api/v1", dependencies=[Depends(require_roles("admin"))])

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.app_name}

@app.get("/hello", include_in_schema=False)
def hello():
    return {"message": "Hello from StockPilot"}
