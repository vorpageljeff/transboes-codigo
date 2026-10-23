from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import func, or_, select

from app.api.v1.dependencies import CurrentUser, Database
from app.api.v1.financial import FinancialWriter
from app.api.v1.router import Writer, apply_trip_status
from app.models.collection import CollectionCase
from app.models.driver import Driver
from app.models.financial import TripCost
from app.models.load import Load, LoadStatus
from app.models.trip import Trip, TripStatus
from app.models.trip_event import TripEvent
from app.models.vehicle import Vehicle, VehicleStatus
from app.modules.audit.service import record_audit
from app.schemas.operations import TripStatusUpdate

router = APIRouter()


class CaseCreate(BaseModel):
    load_id: UUID
    claim_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=5, max_length=3000)
    evidence_reference: str = Field(min_length=3, max_length=500)
    due_date: date | None = None


class CaseTransition(BaseModel):
    status: Literal["COBRADA", "RECEBIDA", "JUSTIFICADA"]
    note: str = Field(min_length=5, max_length=3000)
    received_amount: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=2)
    receipt_reference: str | None = Field(default=None, max_length=500)


def case_json(case):
    return {
        k: getattr(case, k)
        for k in (
            "id",
            "load_id",
            "status",
            "claim_amount",
            "received_amount",
            "reason",
            "evidence_reference",
            "due_date",
            "receipt_reference",
            "created_at",
        )
    }


@router.get("/collections")
def cases(_: CurrentUser, db: Database):
    return [
        case_json(c)
        for c in db.scalars(select(CollectionCase).order_by(CollectionCase.created_at.desc()))
    ]


@router.post("/collections", status_code=201)
def create_case(body: CaseCreate, user: FinancialWriter, db: Database):
    load = db.scalar(select(Load).where(Load.id == body.load_id).with_for_update())
    if not load:
        raise HTTPException(404, "Carga não encontrada")
    if db.scalar(select(CollectionCase.id).where(CollectionCase.load_id == load.id)):
        raise HTTPException(409, "Esta carga já possui acompanhamento")
    case = CollectionCase(**body.model_dump())
    db.add(case)
    db.flush()
    record_audit(
        db,
        user_id=user.id,
        action="COLLECTION_OPENED",
        entity_type="collection_cases",
        entity_id=str(case.id),
        details=body.model_dump(),
    )
    db.commit()
    return case_json(case)


@router.patch("/collections/{case_id}")
def transition(case_id: UUID, body: CaseTransition, user: FinancialWriter, db: Database):
    case = db.scalar(select(CollectionCase).where(CollectionCase.id == case_id).with_for_update())
    if not case:
        raise HTTPException(404, "Cobrança não encontrada")
    allowed = {"EM_REVISAO": {"COBRADA", "JUSTIFICADA"}, "COBRADA": {"RECEBIDA", "JUSTIFICADA"}}
    if body.status not in allowed.get(case.status, set()):
        raise HTTPException(409, "Transição não permitida")
    if body.status == "RECEBIDA":
        if body.received_amount <= 0 or not body.receipt_reference:
            raise HTTPException(422, "Informe valor e referência do comprovante de recebimento")
        if body.received_amount > case.claim_amount:
            raise HTTPException(422, "Recebimento excede o valor cobrado")
        case.received_amount = body.received_amount
        case.receipt_reference = body.receipt_reference
    elif body.received_amount:
        raise HTTPException(422, "Valor recebido somente ao registrar recebimento")
    before = case.status
    case.status = body.status
    record_audit(
        db,
        user_id=user.id,
        action="COLLECTION_TRANSITION",
        entity_type="collection_cases",
        entity_id=str(case.id),
        details={"before": before, **body.model_dump()},
    )
    db.commit()
    return case_json(case)


@router.get("/business/metrics")
def metrics(_: CurrentUser, db: Database):
    return {
        "recovered_amount": db.scalar(
            select(func.coalesce(func.sum(CollectionCase.received_amount), 0))
        ),
        "open_cases": db.scalar(
            select(func.count())
            .select_from(CollectionCase)
            .where(CollectionCase.status.in_(["EM_REVISAO", "COBRADA"]))
        ),
        "note": "Recebimentos de cobranças registrados; não substitui conciliação bancária.",
    }


@router.get("/trips/{trip_id}/result")
def trip_result(trip_id: UUID, _: CurrentUser, db: Database):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404, "Viagem não encontrada")
    costs = list(db.scalars(select(TripCost).where(TripCost.trip_id == trip.id)))
    total = sum((c.amount for c in costs), Decimal(0))
    revenue = trip.load.freight_value
    return {
        "trip_id": trip.id,
        "revenue": revenue,
        "recorded_costs": total,
        "estimated_result": revenue - total if revenue is not None else None,
        "categories_recorded": sorted({c.category.value for c in costs}),
        "costs_complete": False,
        "note": "Resultado parcial: confirme combustível, pedágio, manutenção e demais custos. Receita da carga, sem recebimentos adicionais de cobranças.",
    }


@router.get("/planning/loads/{load_id}/suggestions")
def suggestions(load_id: UUID, _: CurrentUser, db: Database):
    load = db.get(Load, load_id)
    if not load or load.status != LoadStatus.PENDING:
        raise HTTPException(409, "Carga indisponível para programação")
    active = (TripStatus.PLANNED, TripStatus.IN_PROGRESS)
    vehicles = db.scalars(
        select(Vehicle)
        .where(
            Vehicle.status == VehicleStatus.AVAILABLE,
            or_(Vehicle.maintenance_due_km.is_(None), Vehicle.maintenance_due_km > Vehicle.odometer_km),
            or_(Vehicle.maintenance_due_on.is_(None), Vehicle.maintenance_due_on > datetime.now(UTC).date()),
            Vehicle.capacity_kg >= load.weight_kg,
            ~Vehicle.id.in_(select(Trip.vehicle_id).where(Trip.status.in_(active))),
        )
        .order_by(Vehicle.capacity_kg, Vehicle.plate)
    )
    drivers = db.scalars(
        select(Driver)
        .where(
            Driver.is_active.is_(True),
            ~Driver.id.in_(select(Trip.driver_id).where(Trip.status.in_(active))),
        )
        .order_by(Driver.name)
    )
    return {
        "vehicles": [
            {"id": v.id, "plate": v.plate, "capacity_kg": v.capacity_kg} for v in vehicles
        ],
        "drivers": [{"id": d.id, "name": d.name} for d in drivers],
        "basis": "Disponibilidade, capacidade e manutenção cadastrada. Recursos sem prazo de manutenção exigem conferência. Localização e jornada não integradas; confirme com o motorista.",
    }


class EventCreate(BaseModel):
    id: UUID
    status: Literal["EM_ANDAMENTO", "CONCLUIDA", "CANCELADA", "OCORRENCIA"]
    note: str = Field(default="", max_length=3000)
    evidence_reference: str | None = Field(default=None, max_length=500)
    occurred_at: AwareDatetime
    odometer_km: int | None = Field(default=None, ge=0)
    distance_km: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


@router.post("/trips/{trip_id}/events")
def trip_event(trip_id: UUID, body: EventCreate, user: Writer, db: Database):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id).with_for_update())
    if not trip:
        raise HTTPException(404, "Viagem não encontrada")
    existing = db.get(TripEvent, body.id)
    if existing:
        if existing.trip_id != trip_id or existing.user_id != user.id or existing.status != body.status:
            raise HTTPException(409, "Identificador já utilizado em outro evento")
        return {"id": existing.id, "synced": True}
    if body.occurred_at.timestamp() > datetime.now(UTC).timestamp() + 300:
        raise HTTPException(422, "Data do evento está no futuro")
    if body.status != "OCORRENCIA":
        apply_trip_status(trip_id, TripStatusUpdate(status=TripStatus(body.status)), user, db)
    elif len(body.note.strip()) < 5:
        raise HTTPException(422, "Descreva a ocorrência")
    event = TripEvent(**body.model_dump(), trip_id=trip_id, user_id=user.id)
    db.add(event)
    record_audit(db, user_id=user.id, action="TRIP_EVENT", entity_type="trip_events", entity_id=str(event.id), details={"trip_id": trip_id, "status": body.status, "occurred_at": body.occurred_at})
    db.commit()
    return {"id": event.id, "synced": True}


@router.get("/trips/{trip_id}/events")
def list_events(trip_id: UUID, _: CurrentUser, db: Database):
    events = list(db.scalars(select(TripEvent).where(TripEvent.trip_id == trip_id).order_by(TripEvent.occurred_at)))
    return [{"id": e.id, "status": e.status, "note": e.note, "evidence_reference": e.evidence_reference, "occurred_at": e.occurred_at, "odometer_km": e.odometer_km, "distance_km": e.distance_km} for e in events]
