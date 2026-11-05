from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder


def create_purchase_order(
    db: Session, order_data: dict
) -> PurchaseOrder:
    order = PurchaseOrder(**order_data)
    db.add(order)
    db.flush()
    return order


def get_purchase_order_by_id(
    db: Session, order_id: int
) -> PurchaseOrder | None:
    return db.scalars(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    ).first()


def list_purchase_orders(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    supplier_id: int | None = None,
    status: str | None = None,
) -> list[PurchaseOrder]:
    statement = select(PurchaseOrder)
    if supplier_id is not None:
        statement = statement.where(PurchaseOrder.supplier_id == supplier_id)
    if status is not None:
        statement = statement.where(PurchaseOrder.status == status)
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_purchase_order(
    db: Session, order: PurchaseOrder, update_data: dict
) -> PurchaseOrder:
    for field, value in update_data.items():
        setattr(order, field, value)
    db.flush()
    return order
