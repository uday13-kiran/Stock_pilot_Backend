from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Integer,
    Float,
    String,
    DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=True
    )

    forecast_period: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    predicted_demand: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    forecast_method: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    product = relationship("Product")

    warehouse = relationship("Warehouse")