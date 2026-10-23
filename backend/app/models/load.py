import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LoadStatus(str, enum.Enum):
    PENDING = "PENDENTE"
    SCHEDULED = "PROGRAMADA"
    IN_TRANSIT = "EM_TRANSITO"
    DELIVERED = "ENTREGUE"
    CANCELLED = "CANCELADA"


class Load(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "loads"

    reference: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    external_id: Mapped[str | None] = mapped_column(
        String(80), unique=True, index=True, nullable=True
    )
    customer: Mapped[str] = mapped_column(String(160), index=True)
    product: Mapped[str] = mapped_column(String(120))
    origin: Mapped[str] = mapped_column(String(160))
    destination: Mapped[str] = mapped_column(String(160))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    freight_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    expected_freight_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    facility_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="MANUAL")
    pickup_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LoadStatus] = mapped_column(
        Enum(LoadStatus, values_callable=lambda enum: [item.value for item in enum]),
        default=LoadStatus.PENDING,
    )
    trips: Mapped[list["Trip"]] = relationship(back_populates="load")  # noqa: F821
