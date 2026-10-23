import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CostCategory(str, enum.Enum):
    FUEL = "COMBUSTIVEL"
    TOLL = "PEDAGIO"
    MAINTENANCE = "MANUTENCAO"
    OTHER = "OUTRO"


class RevenueEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "revenue_entries"

    load_id: Mapped[UUID] = mapped_column(ForeignKey("loads.id"), unique=True, index=True)
    trip_id: Mapped[UUID | None] = mapped_column(ForeignKey("trips.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    recognized_on: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(40), default="LOAD")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TripCost(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "trip_costs"

    trip_id: Mapped[UUID | None] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id"), index=True)
    category: Mapped[CostCategory] = mapped_column(
        Enum(CostCategory, values_callable=lambda enum: [item.value for item in enum])
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    incurred_on: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(200))
