from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier


def create_supplier(db: Session, supplier_data: dict) -> Supplier:
    supplier = Supplier(**supplier_data)
    db.add(supplier)
    db.flush()
    return supplier


def get_supplier_by_id(db: Session, supplier_id: int) -> Supplier | None:
    return db.scalars(
        select(Supplier).where(Supplier.id == supplier_id)
    ).first()


def list_suppliers(
    db: Session, skip: int = 0, limit: int = 100
) -> list[Supplier]:
    return list(
        db.scalars(select(Supplier).offset(skip).limit(limit)).all()
    )


def update_supplier(
    db: Session, supplier: Supplier, update_data: dict
) -> Supplier:
    for field, value in update_data.items():
        setattr(supplier, field, value)
    db.flush()
    return supplier


def deactivate_supplier(db: Session, supplier: Supplier) -> Supplier:
    supplier.is_active = False
    db.flush()
    return supplier
