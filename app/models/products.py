from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("sku", name="uq_products_sku"),)

    id: Mapped[int] = MappedColumn(Integer, primary_key=True)
    sku: Mapped[str] = MappedColumn(String, nullable=False)
    barcode: Mapped[str | None] = MappedColumn(String(100), nullable=True)
    name: Mapped[str] = MappedColumn(String(150), nullable=False)
    description: Mapped[str | None] = MappedColumn(Text, nullable=True)
    category_id: Mapped[int] = MappedColumn(ForeignKey("categories.id"), nullable=False)
    brand_id: Mapped[int] = MappedColumn(ForeignKey("brands.id"), nullable=False)
    unit_id: Mapped[int] = MappedColumn(ForeignKey("units.id"), nullable=False)
    selling_price: Mapped[Decimal] = MappedColumn(Numeric(10, 2), nullable=False)
    purchase_price: Mapped[Decimal] = MappedColumn(Numeric(10, 2), nullable=False)
    tax_percent: Mapped[Decimal] = MappedColumn(Numeric(5, 2), nullable=False)
    reorder_level: Mapped[int] = MappedColumn(Integer, nullable=False)
    safety_stock: Mapped[int] = MappedColumn(Integer, nullable=False)
    maximum_stock: Mapped[int] = MappedColumn(Integer, nullable=False)
    lead_time: Mapped[int] = MappedColumn(Integer, nullable=False)
    status: Mapped[str] = MappedColumn(String(10), nullable=False, default="ACTIVE")
    is_active: Mapped[bool] = MappedColumn(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = MappedColumn(DateTime, nullable=False, default=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    unit = relationship("Unit", back_populates="products")

    inventories = relationship("Inventory", back_populates="product")
    stock_transactions = relationship("StockTransaction", back_populates="product")
    stock_transfer_items = relationship("StockTransferItem", back_populates="product")
    sale_items = relationship("SaleItem", back_populates="product")
    sales_return_items = relationship("SalesReturnItem", back_populates="product")
    


Products = Product