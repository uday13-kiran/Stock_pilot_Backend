from sqlalchemy import (
    ForeignKey,
    Integer,
    Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SalesReturnItem(Base):
    __tablename__ = "sales_return_items"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    return_id: Mapped[int] = mapped_column(
        ForeignKey("sales_returns.id"),
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

    sales_return = relationship(
        "SalesReturn",
        back_populates="items"
    )

    product = relationship("Product", back_populates="sales_return_items")