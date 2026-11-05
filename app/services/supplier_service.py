from sqlalchemy.orm import Session
from app.repositories import supplier_repo


def create_supplier(db: Session, supplier_data: dict):
    return supplier_repo.create_supplier(db, supplier_data)


def get_supplier(db: Session, supplier_id: int):
    supplier = supplier_repo.get_supplier_by_id(db, supplier_id)
    if supplier is None:
        raise ValueError("Supplier not found")
    return supplier


def update_supplier(db: Session, supplier_id: int, update_data: dict):
    supplier = get_supplier(db, supplier_id)
    return supplier_repo.update_supplier(db, supplier, update_data)


def deactivate_supplier(db: Session, supplier_id: int):
    supplier = get_supplier(db, supplier_id)
    return supplier_repo.deactivate_supplier(db, supplier)
