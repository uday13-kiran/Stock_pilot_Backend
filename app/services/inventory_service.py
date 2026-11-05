"""Central gatekeeper for inventory quantity changes."""
from sqlalchemy.orm import Session
from app.repositories import inventory_repo
from app.rules.stock_rules import (
    validate_non_negative,
    validate_stock_available,
    validate_transfer_quantity,
)


def get_stock(db: Session, product_id: int, warehouse_id: int):
    return inventory_repo.get_inventory(db, product_id, warehouse_id)


def add_stock(db: Session, product_id: int, warehouse_id: int, quantity: int):
    if quantity <= 0:
        raise ValueError("Quantity to add must be greater than zero")
    inventory = get_stock(db, product_id, warehouse_id)
    if inventory is None:
        return inventory_repo.create_inventory(db, {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "quantity": quantity,
            "reserved_quantity": 0,
            "available_quantity": quantity,
        })
    return inventory_repo.update_quantity(db, inventory, inventory.quantity + quantity)


def deduct_stock(db: Session, product_id: int, warehouse_id: int, quantity: int):
    if quantity <= 0:
        raise ValueError("Quantity to deduct must be greater than zero")
    inventory = get_stock(db, product_id, warehouse_id)
    if inventory is None:
        raise ValueError("Inventory record not found")
    validate_stock_available(inventory.available_quantity, quantity)
    return inventory_repo.update_quantity(db, inventory, inventory.quantity - quantity)


def adjust_stock(db: Session, product_id: int, warehouse_id: int, new_quantity: int):
    validate_non_negative(new_quantity)
    inventory = get_stock(db, product_id, warehouse_id)
    if inventory is None:
        raise ValueError("Inventory record not found")
    if new_quantity < inventory.reserved_quantity:
        raise ValueError("Adjusted quantity cannot be below reserved stock")
    return inventory_repo.update_quantity(db, inventory, new_quantity)


def transfer_stock(
    db: Session, product_id: int, source_warehouse_id: int,
    destination_warehouse_id: int, quantity: int,
):
    if source_warehouse_id == destination_warehouse_id:
        raise ValueError("Source and destination warehouses must differ")
    source = get_stock(db, product_id, source_warehouse_id)
    if source is None:
        raise ValueError("Source inventory record not found")
    validate_transfer_quantity(source.available_quantity, quantity)
    destination = get_stock(db, product_id, destination_warehouse_id)
    if destination is None:
        destination = inventory_repo.create_inventory(db, {
            "product_id": product_id,
            "warehouse_id": destination_warehouse_id,
            "quantity": 0,
            "reserved_quantity": 0,
            "available_quantity": 0,
        })
    inventory_repo.update_quantity(db, source, source.quantity - quantity)
    inventory_repo.update_quantity(db, destination, destination.quantity + quantity)
    return source, destination
