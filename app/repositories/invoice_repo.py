from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice


def create_invoice(db: Session, invoice_data: dict) -> Invoice:
    invoice = Invoice(**invoice_data)
    db.add(invoice)
    db.flush()
    return invoice


def get_invoice_by_id(db: Session, invoice_id: int) -> Invoice | None:
    return db.scalars(
        select(Invoice).where(Invoice.id == invoice_id)
    ).first()


def get_invoice_by_number(
    db: Session, invoice_number: str
) -> Invoice | None:
    return db.scalars(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    ).first()


def list_invoices(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> list[Invoice]:
    statement = select(Invoice)
    if status is not None:
        statement = statement.where(Invoice.status == status)
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_invoice(
    db: Session, invoice: Invoice, update_data: dict
) -> Invoice:
    for field, value in update_data.items():
        setattr(invoice, field, value)
    db.flush()
    return invoice
