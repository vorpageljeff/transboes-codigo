import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.api.v1.dependencies import CurrentUser, Database, require_roles
from app.core.config import settings
from app.models.financial import RevenueEntry, TripCost
from app.models.freight import FreightValidation, FreightValidationStatus
from app.models.load import Load
from app.models.trip import Trip
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.modules.audit.service import record_audit
from app.modules.freight.engine import ConfigurableFreightValidationEngine
from app.schemas.financial import (
    CostCreate,
    CostResponse,
    FinancialSummary,
    FreightValidationRequest,
    FreightValidationResponse,
)

router = APIRouter()
FinancialWriter = Annotated[
    User, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.FINANCIAL))
]


def period(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    today = datetime.now(UTC).date()
    start = start_date or today.replace(day=1)
    end = end_date or today
    if start > end:
        raise HTTPException(status_code=422, detail="Período inválido")
    return start, end


def build_summary(db: Database, start: date, end: date) -> FinancialSummary:
    revenue = db.scalar(
        select(func.coalesce(func.sum(RevenueEntry.amount), 0)).where(
            RevenueEntry.recognized_on.between(start, end)
        )
    ) or Decimal(0)
    costs = db.scalar(
        select(func.coalesce(func.sum(TripCost.amount), 0)).where(
            TripCost.incurred_on.between(start, end)
        )
    ) or Decimal(0)
    load_count = (
        db.scalar(
            select(func.count())
            .select_from(RevenueEntry)
            .where(RevenueEntry.recognized_on.between(start, end))
        )
        or 0
    )
    validations = list(
        db.scalars(
            select(FreightValidation)
            .join(Load, FreightValidation.load_id == Load.id)
            .where(
                func.coalesce(Load.delivery_date, func.date(FreightValidation.created_at)).between(
                    start, end
                )
            )
        )
    )
    latest = {}
    for item in sorted(validations, key=lambda v: (v.created_at, str(v.id)), reverse=True):
        latest.setdefault(item.load_id, item)
    validations = list(latest.values())
    divergent = [item for item in validations if item.status == FreightValidationStatus.DIVERGENT]
    return FinancialSummary(
        start_date=start,
        end_date=end,
        revenue=revenue,
        costs=costs,
        estimated_margin=revenue - costs,
        load_count=load_count,
        checked_freights=sum(
            item.status in {FreightValidationStatus.OK, FreightValidationStatus.MANUALLY_ADJUSTED}
            for item in validations
        ),
        divergent_freights=len(divergent),
        divergent_amount=sum(
            (abs(item.difference or Decimal(0)) for item in divergent), Decimal(0)
        ),
    )


@router.get("/financial/summary", response_model=FinancialSummary, tags=["financial"])
def financial_summary(
    _: CurrentUser,
    db: Database,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> FinancialSummary:
    start, end = period(start_date, end_date)
    return build_summary(db, start, end)


@router.get("/financial/costs", response_model=list[CostResponse], tags=["financial"])
def list_costs(_: CurrentUser, db: Database) -> list[TripCost]:
    return list(db.scalars(select(TripCost).order_by(TripCost.incurred_on.desc())))


@router.post("/financial/costs", response_model=CostResponse, status_code=201, tags=["financial"])
def create_cost(body: CostCreate, user: FinancialWriter, db: Database) -> TripCost:
    if not db.get(Vehicle, body.vehicle_id):
        raise HTTPException(status_code=422, detail="Veículo inválido")
    if body.trip_id:
        trip = db.get(Trip, body.trip_id)
        if not trip or trip.vehicle_id != body.vehicle_id:
            raise HTTPException(status_code=422, detail="Viagem incompatível com o veículo")
    cost = TripCost(**body.model_dump())
    db.add(cost)
    db.flush()
    record_audit(
        db,
        user_id=user.id,
        action="FINANCIAL_COST_CREATED",
        entity_type="trip_cost",
        entity_id=str(cost.id),
        details={"amount": cost.amount, "category": cost.category.value},
    )
    db.commit()
    db.refresh(cost)
    return cost


@router.get(
    "/freight/validations", response_model=list[FreightValidationResponse], tags=["freight"]
)
def list_validations(_: CurrentUser, db: Database) -> list[FreightValidation]:
    return list(db.scalars(select(FreightValidation).order_by(FreightValidation.created_at.desc())))


@router.post(
    "/freight/loads/{load_id}/validate",
    response_model=FreightValidationResponse,
    status_code=201,
    tags=["freight"],
)
def validate_freight(
    load_id: UUID, body: FreightValidationRequest, user: FinancialWriter, db: Database
) -> FreightValidation:
    load = db.get(Load, load_id)
    if not load or load.freight_value is None:
        raise HTTPException(status_code=422, detail="Carga sem valor de frete recebido")
    engine = ConfigurableFreightValidationEngine(settings.freight_validation_mode)
    result = engine.validate(load.freight_value, body.expected_amount)
    validation = FreightValidation(
        load_id=load.id,
        mode=settings.freight_validation_mode,
        received_amount=result.received_amount,
        expected_amount=result.expected_amount,
        difference=result.difference,
        status=result.status,
        explanation=result.explanation,
    )
    db.add(validation)
    db.flush()
    record_audit(
        db,
        user_id=user.id,
        action="FREIGHT_VALIDATED",
        entity_type="freight_validation",
        entity_id=str(validation.id),
        details={"load_id": load.id, "status": validation.status.value, "mode": validation.mode},
    )
    db.commit()
    db.refresh(validation)
    return validation


@router.get("/reports/billing.csv", tags=["reports"])
def billing_csv(
    _: CurrentUser,
    db: Database,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> StreamingResponse:
    start, end = period(start_date, end_date)
    rows = db.execute(
        select(RevenueEntry, Load)
        .join(Load, RevenueEntry.load_id == Load.id)
        .where(RevenueEntry.recognized_on.between(start, end))
        .order_by(RevenueEntry.recognized_on)
    )
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["data", "referencia", "cliente", "origem", "destino", "valor"])

    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value

    for revenue, load in rows:
        writer.writerow(
            [
                revenue.recognized_on,
                safe(load.reference),
                safe(load.customer),
                safe(load.origin),
                safe(load.destination),
                revenue.amount,
            ]
        )
    headers = {"Content-Disposition": f'attachment; filename="faturamento_{start}_{end}.csv"'}
    return StreamingResponse(
        iter([stream.getvalue()]), media_type="text/csv; charset=utf-8", headers=headers
    )
