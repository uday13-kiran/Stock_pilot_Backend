from datetime import datetime

from sqlalchemy import (ForeignKey, Integer, DateTime, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"), CheckConstraint("quantity >= 0", name="ck_inventory_nonnegative"))

    id: Mapped[int] = mapped_column(primary_key=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    reserved_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    available_quantity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    product = relationship(
        "Product",
        back_populates="inventories"
    )

    warehouse = relationship(
        "Warehouse",
        back_populates="inventory"
    )