from sqlalchemy import (
    ForeignKey,
    Integer
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StockTransferItem(Base):
    __tablename__ = "stock_transfer_items"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    transfer_id: Mapped[int] = mapped_column(
        ForeignKey("stock_transfers.id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    requested_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    dispatched_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    received_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    transfer = relationship(
        "StockTransfer",
        back_populates="items"
    )

    product = relationship("Product", back_populates="stock_transfer_items")