"""Product use-cases; routes translate these errors into HTTP responses."""
from sqlalchemy.orm import Session
from app.repositories import product_repo
from app.schemas.product import ProductCreate, ProductUpdate


def _data(value):
    return value.model_dump(exclude_unset=True) if hasattr(value, "model_dump") else dict(value)


def create_product(product_data: ProductCreate | dict, db: Session):
    payload = _data(product_data)
    sku = payload.get("sku")
    if sku and product_repo.get_product_by_sku(db, sku):
        raise ValueError("Product SKU already exists")
    return product_repo.create_product(db, payload)


def get_product(product_id: int, db: Session):
    product = product_repo.get_product_by_id(db, product_id)
    if product is None:
        raise ValueError("Product not found")
    return product


def list_products(db: Session, skip: int = 0, limit: int = 100):
    if skip < 0 or not 1 <= limit <= 200:
        raise ValueError("skip must be >= 0 and limit must be between 1 and 200")
    return product_repo.list_products(db, skip, limit)


def update_product(data: ProductUpdate, db: Session, product_id: int):
    product = get_product(product_id, db)
    payload = _data(data)
    if "sku" in payload and payload["sku"] != product.sku:
        existing = product_repo.get_product_by_sku(db, payload["sku"])
        if existing is not None:
            raise ValueError("Product SKU already exists")
    return product_repo.update_product(db, product, payload)


def deactivate_product(product_id: int, db: Session):
    product = get_product(product_id, db)
    return product_repo.deactivate_product(db, product)
