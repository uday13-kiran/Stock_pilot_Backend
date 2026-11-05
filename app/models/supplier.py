from sqlalchemy import ForeignKey,String
from sqlalchemy.orm import Mapped, mapped_column,relationship

from app.core.database import Base
class Supplier(Base):
    __tablename__= "suppliers"

    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(String(200),nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email : Mapped[str | None] = mapped_column(String(500),nullable=True,unique=True)
    phone : Mapped[str | None] = mapped_column(String(50),nullable=True,unique=True)
    address : Mapped[str | None] = mapped_column(String(500),nullable=True)
    is_active : Mapped[bool] = mapped_column(nullable=False,default=True)
    products = relationship("SupplierProduct", back_populates="supplier")