from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment


def create_payment(db: Session, payment_data: dict) -> Payment:
    payment = Payment(**payment_data)
    db.add(payment)
    db.flush()
    return payment


def get_payment_by_id(db: Session, payment_id: int) -> Payment | None:
    return db.scalars(
        select(Payment).where(Payment.id == payment_id)
    ).first()


def list_payments(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    invoice_id: int | None = None,
) -> list[Payment]:
    statement = select(Payment)
    if invoice_id is not None:
        statement = statement.where(Payment.invoice_id == invoice_id)
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_payments_by_invoice(
    db: Session, invoice_id: int
) -> list[Payment]:
    statement = select(Payment).where(Payment.invoice_id == invoice_id)
    return list(db.scalars(statement).all())
