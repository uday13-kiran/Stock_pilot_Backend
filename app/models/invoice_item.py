from sqlalchemy import (
    ForeignKey,
    Integer,
    Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    unit_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    total_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    invoice = relationship(
        "Invoice",
        back_populates="items"
    )

    product = relationship("Product")