from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SalesReturn(Base):
    __tablename__ = "sales_returns"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"),
        nullable=False
    )

    return_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    items = relationship(
        "SalesReturnItem",
        back_populates="sales_return"
    )

    sale = relationship("Sale", back_populates="sales_returns")