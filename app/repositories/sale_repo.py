from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sale import Sale


def create_sale(db: Session, sale_data: dict) -> Sale:
    sale = Sale(**sale_data)
    db.add(sale)
    db.flush()
    return sale


def get_sale_by_id(db: Session, sale_id: int) -> Sale | None:
    return db.scalars(
        select(Sale).where(Sale.id == sale_id)
    ).first()


def list_sales(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> list[Sale]:
    statement = select(Sale)
    if status is not None:
        statement = statement.where(Sale.status == status)
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())
