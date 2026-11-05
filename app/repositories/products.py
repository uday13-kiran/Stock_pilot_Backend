from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.products import Products

def create_product(db:Session,product_data:dict)->Products:
    product = Products(**product_data)

    db.add(product)
    db.flush()

    return product

def get_product_by_id(db:Session,product_id:int)->Products|None:
    statement = select(Products).where(Products.id==product_id)
    return db.scalars(statement).first()

def get_product_by_sku(db:Session,product_sku:int)->Products|None:
    statement = select(Products).where(Products.sku==product_sku)
    return db.scalars(statement).first()

def list_products(db:Session,skip:int = 0,limit:int =100 )->list[Products]:
    statement = (select(Products).offset(skip).limit(limit))
    return list(db.scalars(statement).all())

def update_product( db: Session,product: Products,update_data: dict) -> Products:
    for field, value in update_data.items():
        setattr(product, field, value)

    db.flush()

    return product


def deactivate_product(db: Session,product: Products) -> Products:
    product.is_active = False
    db.flush()
    return product