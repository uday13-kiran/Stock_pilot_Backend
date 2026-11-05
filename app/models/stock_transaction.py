from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False
    )

    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    product = relationship("Product", back_populates="stock_transactions")

    warehouse = relationship("Warehouse")