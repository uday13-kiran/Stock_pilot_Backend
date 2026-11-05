from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Float,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"),
        nullable=False
    )

    invoice_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    subtotal: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    tax_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    total_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    items = relationship(
        "InvoiceItem",
        back_populates="invoice"
    )

    payments = relationship(
        "Payment",
        back_populates="invoice"
    )

    sale = relationship("Sale", back_populates="invoices")