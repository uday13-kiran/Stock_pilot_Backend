from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Float,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False
    )

    sale_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    subtotal: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0
    )

    discount_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0
    )

    tax_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0
    )

    total_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    customer = relationship(
        "Customer",
        back_populates="sales"
    )

    items = relationship(
        "SaleItem", back_populates="sale", cascade="all, delete-orphan"
    )
    invoices = relationship("Invoice", back_populates="sale")
    sales_returns = relationship("SalesReturn", back_populates="sale")
    user = relationship("User")
    warehouse = relationship("Warehouse")