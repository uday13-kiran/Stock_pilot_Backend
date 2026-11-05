from sqlalchemy import (
    ForeignKey,
    Integer
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReorderRule(Base):
    __tablename__ = "reorder_rules"

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

    reorder_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    safety_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    maximum_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    product = relationship("Product")

    warehouse = relationship("Warehouse")