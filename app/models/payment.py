from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Float,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id"),
        nullable=False
    )

    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    payment_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    invoice = relationship(
        "Invoice",
        back_populates="payments"
    )