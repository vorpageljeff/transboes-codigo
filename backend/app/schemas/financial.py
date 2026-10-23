from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.financial import CostCategory
from app.models.freight import FreightValidationStatus


class FinancialSummary(BaseModel):
    start_date: date
    end_date: date
    revenue: Decimal
    costs: Decimal
    estimated_margin: Decimal
    load_count: int
    checked_freights: int
    divergent_freights: int
    divergent_amount: Decimal


class CostCreate(BaseModel):
    vehicle_id: UUID
    trip_id: UUID | None = None
    category: CostCategory
    amount: Decimal = Field(gt=0)
    incurred_on: date
    description: str = Field(min_length=2, max_length=200)


class CostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    vehicle_id: UUID
    trip_id: UUID | None
    category: CostCategory
    amount: Decimal
    incurred_on: date
    description: str


class FreightValidationRequest(BaseModel):
    expected_amount: Decimal | None = Field(default=None, ge=0)


class FreightValidationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    load_id: UUID
    mode: str
    received_amount: Decimal
    expected_amount: Decimal | None
    difference: Decimal | None
    status: FreightValidationStatus
    explanation: str
    created_at: datetime
