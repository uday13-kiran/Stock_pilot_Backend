from sqlalchemy.orm import Session
from app.repositories import purchase_order_repo
from app.rules.purchase_rules import validate_purchase_status, validate_receive_quantity


def create_purchase_order(db: Session, order_data: dict):
    return purchase_order_repo.create_purchase_order(db, order_data)


def get_purchase_order(db: Session, order_id: int):
    order = purchase_order_repo.get_purchase_order_by_id(db, order_id)
    if order is None:
        raise ValueError("Purchase order not found")
    return order


def update_purchase_order_status(db: Session, order_id: int, status: str):
    validate_purchase_status(status)
    order = get_purchase_order(db, order_id)
    return purchase_order_repo.update_purchase_order(
        db, order, {"status": status.strip().upper()}
    )


def validate_receipt(ordered_quantity: int, already_received_quantity: int,receiving_quantity: int) -> None:
    validate_receive_quantity(ordered_quantity, already_received_quantity,  receiving_quantity)
