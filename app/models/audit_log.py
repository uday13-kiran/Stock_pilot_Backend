from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    String,
    DateTime,
    Integer
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    details: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="audit_logs"
    )