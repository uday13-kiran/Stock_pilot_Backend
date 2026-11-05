from sqlalchemy.orm import Session
from app.repositories import invoice_repo


def create_invoice(db: Session, invoice_data: dict):
    """Validate sale and calculate trusted totals before calling in production."""
    return invoice_repo.create_invoice(db, invoice_data)


def get_invoice(db: Session, invoice_id: int):
    invoice = invoice_repo.get_invoice_by_id(db, invoice_id)
    if invoice is None:
        raise ValueError("Invoice not found")
    return invoice


def update_invoice(db: Session, invoice_id: int, update_data: dict):
    invoice = get_invoice(db, invoice_id)
    return invoice_repo.update_invoice(db, invoice, update_data)
