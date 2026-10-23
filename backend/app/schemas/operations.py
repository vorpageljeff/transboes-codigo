from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.load import LoadStatus
from app.models.trip import TripStatus
from app.models.vehicle import VehicleStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VehicleCreate(BaseModel):
    plate: str = Field(min_length=7, max_length=10)
    model: str = Field(min_length=2, max_length=120)
    capacity_kg: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SafePatch(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def reject_null(cls, values):
        nullable = {"phone", "notes", "pickup_date", "delivery_date", "freight_value", "maintenance_due_km", "maintenance_due_on"}
        if isinstance(values, dict) and any(
            v is None and k not in nullable for k, v in values.items()
        ):
            raise ValueError("Campo obrigatório não pode ser nulo")
        return values


class VehicleUpdate(SafePatch):
    odometer_km: int | None = Field(default=None, ge=0)
    maintenance_due_km: int | None = Field(default=None, ge=0)
    maintenance_due_on: date | None = None
    model: str | None = Field(default=None, min_length=2, max_length=120)
    capacity_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    status: VehicleStatus | None = None


class VehicleResponse(ORMModel):
    odometer_km: int
    maintenance_due_km: int | None
    maintenance_due_on: date | None
    id: UUID
    plate: str
    model: str
    capacity_kg: Decimal
    status: VehicleStatus


class DriverCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    license_number: str = Field(min_length=3, max_length=30)


class DriverUpdate(SafePatch):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None


class DriverResponse(ORMModel):
    id: UUID
    name: str
    phone: str | None
    license_number: str
    is_active: bool


class LoadCreate(BaseModel):
    reference: str = Field(min_length=1, max_length=50)
    customer: str = Field(min_length=2, max_length=160)
    product: str = Field(min_length=2, max_length=120)
    origin: str = Field(min_length=2, max_length=160)
    destination: str = Field(min_length=2, max_length=160)
    weight_kg: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    freight_value: Decimal | None = Field(default=None, ge=0)
    expected_freight_value: Decimal | None = Field(default=None, ge=0)
    distance_km: Decimal | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, ge=0)
    facility_code: str | None = Field(default=None, max_length=20)
    pickup_date: date | None = None
    delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=3000)


class LoadUpdate(SafePatch):
    customer: str | None = Field(default=None, min_length=2, max_length=160)
    product: str | None = Field(default=None, min_length=2, max_length=120)
    origin: str | None = Field(default=None, min_length=2, max_length=160)
    destination: str | None = Field(default=None, min_length=2, max_length=160)
    weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    freight_value: Decimal | None = Field(default=None, ge=0)
    pickup_date: date | None = None
    delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=3000)
    status: LoadStatus | None = None


class LoadResponse(ORMModel):
    id: UUID
    reference: str
    customer: str
    product: str
    origin: str
    destination: str
    weight_kg: Decimal
    freight_value: Decimal | None
    expected_freight_value: Decimal | None
    distance_km: Decimal | None
    quantity: int | None
    facility_code: str | None
    source: str
    pickup_date: date | None
    delivery_date: date | None
    notes: str | None
    status: LoadStatus


class TripCreate(BaseModel):
    load_id: UUID
    vehicle_id: UUID
    driver_id: UUID
    scheduled_at: datetime
    notes: str | None = Field(default=None, max_length=3000)


class TripStatusUpdate(BaseModel):
    status: TripStatus


class TripResponse(ORMModel):
    id: UUID
    load_id: UUID
    vehicle_id: UUID
    driver_id: UUID
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    notes: str | None
    status: TripStatus
    load: LoadResponse
    vehicle: VehicleResponse
    driver: DriverResponse


class DashboardResponse(BaseModel):
    pending_loads: int
    available_vehicles: int
    active_trips: int
    occurrences: int
