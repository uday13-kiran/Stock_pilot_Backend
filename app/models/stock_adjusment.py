from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    DateTime,
    Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"

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

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    approved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    product = relationship("Product")

    warehouse = relationship("Warehouse")

    user = relationship("User")