from sqlalchemy.orm import Session
from app.repositories import sale_repo
from app.rules.sales_rules import validate_sale_quantity
from app.services import inventory_service


def create_sale(db: Session, sale_data: dict):
    """Starter only: coordinate line items and stock in one transaction in production."""
    return sale_repo.create_sale(db, sale_data)


def validate_and_deduct_sale_stock(
    db: Session, product_id: int, warehouse_id: int,
    available_quantity: int, sale_quantity: int,
):
    validate_sale_quantity(available_quantity, sale_quantity)
    return inventory_service.deduct_stock(
        db, product_id, warehouse_id, sale_quantity
    )
