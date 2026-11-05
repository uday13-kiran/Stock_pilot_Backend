
from sqlalchemy.orm import Session

from app.models.products import Product
from app.models.warehouse import Warehouse
from app.schemas.inventory import InventoryCreate
from app.repositories import inventory_repo


def create_inventory(
    db: Session,
    data: InventoryCreate,
):
    # 1. Check that the product exists.
    product = db.get(Product, data.product_id)

    if product is None:
        raise ValueError("Product not found")

    # 2. Check that the warehouse exists.
    warehouse = db.get(Warehouse, data.warehouse_id)

    if warehouse is None:
        raise ValueError("Warehouse not found")

    # 3. Prevent duplicate inventory records.
    existing = inventory_repo.get_inventory(
        db,
        data.product_id,
        data.warehouse_id,
    )

    if existing is not None:
        raise ValueError(
            "Inventory already exists for this product "
            "and warehouse"
        )

    inventory_data = data.model_dump()

    inventory_data["available_quantity"] = (
        data.quantity - data.reserved_quantity
    )

    return inventory_repo.create_inventory(
        db,
        inventory_data,
    )