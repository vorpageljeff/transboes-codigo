import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TripStatus(str, enum.Enum):
    PLANNED = "PLANEJADA"
    IN_PROGRESS = "EM_ANDAMENTO"
    COMPLETED = "CONCLUIDA"
    CANCELLED = "CANCELADA"


class Trip(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "trips"

    load_id: Mapped[UUID] = mapped_column(ForeignKey("loads.id"), index=True)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id"), index=True)
    driver_id: Mapped[UUID] = mapped_column(ForeignKey("drivers.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TripStatus] = mapped_column(
        Enum(TripStatus, values_callable=lambda enum: [item.value for item in enum]),
        default=TripStatus.PLANNED,
    )
    load: Mapped["Load"] = relationship(back_populates="trips")  # noqa: F821
    vehicle: Mapped["Vehicle"] = relationship()  # noqa: F821
    driver: Mapped["Driver"] = relationship()  # noqa: F821
