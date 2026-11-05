from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.inventory import Inventory
from app.models.products import Product
from app.models.reorder_rule import ReorderRule
from app.models.warehouse import Warehouse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/low-stock")
def low_stock_notifications(
    db: Session = Depends(get_db),
    _authorized=Depends(
        require_roles(
            "admin",
            "inventory_manager",
            "purchase_manager",
            "warehouse_staff",
            "sales_staff",
            "finance_billing_staff",
        )
    ),
):
    rows = db.execute(
        select(
            Inventory,
            Product,
            Warehouse,
            func.coalesce(ReorderRule.reorder_level, Product.reorder_level),
            func.coalesce(ReorderRule.safety_stock, Product.safety_stock),
        )
        .join(Product, Product.id == Inventory.product_id)
        .join(Warehouse, Warehouse.id == Inventory.warehouse_id)
        .outerjoin(
            ReorderRule,
            and_(
                ReorderRule.product_id == Inventory.product_id,
                ReorderRule.warehouse_id == Inventory.warehouse_id,
            ),
        )
        .where(
            Inventory.available_quantity
            <= func.coalesce(ReorderRule.reorder_level, Product.reorder_level)
        )
        .order_by(Inventory.available_quantity, Product.name, Warehouse.name)
    ).all()

    items = []
    for inventory, product, warehouse, reorder_level, safety_stock in rows:
        severity = "CRITICAL" if inventory.available_quantity <= safety_stock else "LOW"
        items.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "sku": product.sku,
                "warehouse_id": warehouse.id,
                "warehouse_name": warehouse.name,
                "warehouse_location": warehouse.location,
                "quantity": inventory.quantity,
                "reserved_quantity": inventory.reserved_quantity,
                "available_quantity": inventory.available_quantity,
                "reorder_level": reorder_level,
                "safety_stock": safety_stock,
                "severity": severity,
                "title": f"{severity.title()} stock: {product.name}",
                "message": (
                    f"{warehouse.name} has {inventory.available_quantity} units available; "
                    f"the reorder level is {reorder_level}."
                ),
                "updated_at": inventory.updated_at,
            }
        )

    return {"count": len(items), "items": items}
