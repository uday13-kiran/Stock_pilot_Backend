from sqlalchemy import ForeignKey, String, DateTime, Numeric
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class PurchaseOrder(Base):
    __tablename__= "purchase_order"

    id : Mapped[int] = mapped_column(primary_key=True)
    supplier_id : Mapped[int] = mapped_column(ForeignKey("suppliers.id"),nullable=False)
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True, index=True)
    user_id : Mapped[int] = mapped_column(ForeignKey("users.id"),nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True) 
    status : Mapped[str] = mapped_column(String(50),nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")
    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")
    user = relationship("User")