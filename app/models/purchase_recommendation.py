from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PurchaseRecommendation(Base):
    __tablename__ = "purchase_recommendations"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=True
    )

    suggested_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    priority: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    reason: Mapped[str] = mapped_column(
        String(1000),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    product = relationship("Product")

    warehouse = relationship("Warehouse")