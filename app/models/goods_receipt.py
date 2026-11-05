from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_order.id"),
        nullable=False
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False
    )

    received_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    items = relationship(
        "GoodsReceiptItem",
        back_populates="goods_receipt"
    )

    purchase_order = relationship(
        "PurchaseOrder"
    )

    warehouse = relationship(
        "Warehouse"
    )
    