from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.products import Product


def create_product(db: Session, product_data: dict) -> Product:
    product = Product(**product_data)
    db.add(product)
    db.flush()
    return product


def get_product_by_id(db: Session, product_id: int) -> Product | None:
    return db.scalars(
        select(Product).where(Product.id == product_id)
    ).first()


def get_product_by_sku(db: Session, sku: str) -> Product | None:
    return db.scalars(
        select(Product).where(Product.sku == sku)
    ).first()


def list_products(
    db: Session, skip: int = 0, limit: int = 100
) -> list[Product]:
    statement = select(Product).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_product(
    db: Session, product: Product, update_data: dict
) -> Product:
    for field, value in update_data.items():
        setattr(product, field, value)
    db.flush()
    return product


def deactivate_product(db: Session, product: Product) -> Product:
    product.is_active = False
    db.flush()
    return product
