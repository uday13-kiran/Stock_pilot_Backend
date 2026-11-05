from sqlalchemy import (
    ForeignKey,
    Integer,
    Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"),
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

    discount_amount: Mapped[float] = mapped_column(
        Float,
        default=0,
        nullable=False
    )

    tax_amount: Mapped[float] = mapped_column(
        Float,
        default=0,
        nullable=False
    )

    total_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    sale = relationship(
        "Sale",
        back_populates="items"
    )

    product = relationship(
        "Product",
        back_populates="sale_items"
    )