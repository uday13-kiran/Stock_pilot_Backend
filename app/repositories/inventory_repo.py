from sqlalchemy import select
from sqlalchemy.orm import session 


from app.models.inventory import Inventory

def get_inventory(db:session,product_id:int,warehouse_id:int)->Inventory|None:
    statement = select(Inventory).where(Inventory.product_id==product_id,Inventory.warehouse==warehouse_id)
    return db.scalar(statement)

def create_inventory(db:session,inventory_data:dict)->Inventory:
    inventory = Inventory(**inventory_data)

    db.add(inventory)
    db.flush()
    return inventory

def update_inventory(db:session,inventory_data:dict)->Inventory:
    inventory = Inventory(**inventory_data)
    
    db.add(inventory)
    db.flush()
    return inventory

def update_quantity(db:session,inventory:Inventory,quantity:int)->Inventory:
    inventory.quantity = quantity
    inventory.available_quantity = (quantity - inventory.reserved_quantity)

    db.flush()
    return inventory

def list_inventory(db:session,warehouse_id:int | None=None)->list[Inventory]:
    statement = select(Inventory)
    if warehouse_id is not None:
        statement = statement.where(
            Inventory.warehouse_id == warehouse_id)

    return list(db.scalars(statement).all())