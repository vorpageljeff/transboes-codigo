from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VehiclePosition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vehicle_positions"
    __table_args__ = (
        Index("ix_vehicle_positions_vehicle_captured", "vehicle_id", "captured_at"),
    )

    vehicle_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(9, 2), nullable=True)
    speed_kmh: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    heading: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(40), default="MOBILE_BROWSER")
