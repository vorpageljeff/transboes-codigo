import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "DISPONIVEL"
    RESERVED = "RESERVADO"
    ON_ROUTE = "EM_ROTA"
    UNLOADING = "DESCARGA"
    RETURNING = "RETORNO_BASE"
    MAINTENANCE = "MANUTENCAO"
    INACTIVE = "INATIVO"


class Vehicle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vehicles"

    plate: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    model: Mapped[str] = mapped_column(String(120))
    capacity_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus, values_callable=lambda enum: [item.value for item in enum]),
        default=VehicleStatus.AVAILABLE,
    )

    odometer_km: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    maintenance_due_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maintenance_due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
