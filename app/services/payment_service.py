from decimal import Decimal
from sqlalchemy.orm import Session
from app.repositories import payment_repo


def create_payment(db: Session, payment_data: dict):
    amount = payment_data.get("amount")
    if amount is not None and Decimal(str(amount)) <= 0:
        raise ValueError("Payment amount must be greater than zero")
    # Add invoice existence and outstanding-balance validation for your models.
    return payment_repo.create_payment(db, payment_data)


def get_payment(db: Session, payment_id: int):
    payment = payment_repo.get_payment_by_id(db, payment_id)
    if payment is None:
        raise ValueError("Payment not found")
    return payment
