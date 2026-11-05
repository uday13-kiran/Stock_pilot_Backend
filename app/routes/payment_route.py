"""Payment recording endpoints with invoice-balance and idempotency checks.

This is a manual payment-recording workflow, not a payment gateway integration.
A payment is marked PAID only when an authorized finance user confirms receipt.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.operational_events import record_event
from app.models.invoice import Invoice
from app.models.payment import Payment

router = APIRouter(tags=["Payments"])
ALLOWED_METHODS = {"CASH", "CARD", "UPI", "BANK_TRANSFER", "CREDIT"}

class PaymentRecordRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: str

@router.post("/invoices/{invoice_id}/payments", status_code=201)
def record_invoice_payment(
    invoice_id: int,
    payload: PaymentRecordRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    _authorized=Depends(require_roles("finance_billing_staff")),
):
    try:
        if idempotency_key:
            if len(idempotency_key) > 120:
                raise HTTPException(status_code=422, detail="Idempotency-Key must be at most 120 characters")
            prior = db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
            if prior:
                requested_amount = payload.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if prior.invoice_id != invoice_id or Decimal(str(prior.amount)).quantize(Decimal("0.01")) != requested_amount or prior.payment_method != payload.payment_method.strip().upper():
                    raise HTTPException(status_code=409, detail="Idempotency key was already used for a different payment")
                return {"payment_id": prior.id, "invoice_id": prior.invoice_id, "amount": str(prior.amount), "status": prior.status, "idempotent_replay": True}
        invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        method = payload.payment_method.strip().upper()
        if method not in ALLOWED_METHODS:
            raise HTTPException(status_code=422, detail=f"Unsupported payment method. Choose one of: {', '.join(sorted(ALLOWED_METHODS))}")
        paid = Decimal(str(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == invoice_id, Payment.status == "PAID")) or 0)).quantize(Decimal("0.01"))
        total = Decimal(str(invoice.total_amount)).quantize(Decimal("0.01"))
        amount = payload.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount > total - paid:
            raise HTTPException(status_code=409, detail=f"Payment exceeds remaining invoice balance of {total - paid}")
        payment = Payment(invoice_id=invoice_id, amount=float(amount), payment_method=method, payment_date=datetime.utcnow(), status="PAID", idempotency_key=idempotency_key)
        db.add(payment); db.flush()
        new_paid = paid + amount
        invoice.status = "PAID" if new_paid >= total else "PARTIALLY_PAID"
        db.commit(); db.refresh(payment)
        record_event("payment.recorded", "payment", payment.id, {"invoice_id": invoice_id, "amount": str(amount), "method": method, "invoice_status": invoice.status})
        return {"payment_id": payment.id, "invoice_id": invoice_id, "amount": str(amount), "amount_paid": str(new_paid), "balance_due": str(total-new_paid), "invoice_status": invoice.status, "status": payment.status, "idempotent_replay": False}
    except Exception:
        db.rollback()
        raise

@router.get("/payments/")
def list_payments(db: Session = Depends(get_db), _authorized=Depends(require_roles("finance_billing_staff"))):
    rows = db.scalars(select(Payment).order_by(Payment.payment_date.desc())).all()
    return [{"id": p.id, "invoice_id": p.invoice_id, "amount": str(p.amount), "payment_method": p.payment_method, "payment_date": p.payment_date.isoformat(), "status": p.status} for p in rows]
