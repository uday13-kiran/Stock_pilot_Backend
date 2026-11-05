from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    from_warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False
    )

    to_warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False
    )

    transfer_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REQUESTED"
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    items = relationship(
        "StockTransferItem",
        back_populates="transfer"
    )

    source_warehouse = relationship(
        "Warehouse",
        foreign_keys=[from_warehouse_id]
    )

    destination_warehouse = relationship(
        "Warehouse",
        foreign_keys=[to_warehouse_id]
    )