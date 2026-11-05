from sqlalchemy import ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id: Mapped[int] = mapped_column(primary_key=True)

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    supplier_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    supplier = relationship(
        "Supplier",
        back_populates="products"
    )

    product = relationship("Product")