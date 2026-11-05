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


class StockAlert(Base):
    __tablename__ = "stock_alerts"

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

    current_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    reorder_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    alert_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    is_resolved: Mapped[bool] = mapped_column(
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