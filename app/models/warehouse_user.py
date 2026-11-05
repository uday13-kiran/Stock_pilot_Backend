from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WarehouseUser(Base):
    __tablename__ = "warehouse_users"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False
    )

    role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    user = relationship("User", back_populates="warehouse_links")

    warehouse = relationship(
        "Warehouse",
        back_populates="users"
    )