import json
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies import CurrentUser, Database, require_roles
from app.api.v1.router import Writer, reconcile
from app.core.config import settings
from app.models.freight import FreightCalculation, FreightRuleSet, FreightRuleVersion
from app.models.load import Load, LoadStatus
from app.models.load_version import LoadVersion
from app.models.location import Location
from app.models.trip import Trip, TripStatus
from app.models.user import User, UserRole
from app.modules.audit.service import record_audit

router = APIRouter()
Manager = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))]


class LocationBody(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    kind: str = Field(min_length=2, max_length=40)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    source: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def coordinates_together(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Informe latitude e longitude juntas")
        return self


@router.get("/locations", tags=["locations"])
def locations(_: CurrentUser, db: Database):
    return list(db.scalars(select(Location).order_by(Location.name)))


@router.post("/locations", status_code=201, tags=["locations"])
def create_location(body: LocationBody, user: Writer, db: Database):
    item = Location(**body.model_dump())
    db.add(item)
    db.flush()
    record_audit(db, user_id=user.id, action="LOCATION_CREATED", entity_type="locations", entity_id=str(item.id), details=body.model_dump())
    db.commit()
    db.refresh(item)
    return item


@router.patch("/locations/{location_id}", tags=["locations"])
def update_location(location_id: UUID, body: LocationBody, user: Writer, db: Database):
    item = db.scalar(select(Location).where(Location.id == location_id).with_for_update())
    if not item:
        raise HTTPException(404, "Localização não encontrada")
    before = {key: getattr(item, key) for key in body.model_fields}
    for key, value in body.model_dump().items():
        setattr(item, key, value)
    record_audit(db, user_id=user.id, action="LOCATION_UPDATED", entity_type="locations", entity_id=str(item.id), details={"before": before, "after": body.model_dump()})
    db.commit()
    db.refresh(item)
    return item


def load_snapshot(load: Load) -> dict:
    return {column.name: getattr(load, column.name) for column in load.__table__.columns}


def save_version(db: Database, load: Load, user: User, action: str, reason: str | None = None):
    number = db.scalar(select(func.max(LoadVersion.version)).where(LoadVersion.load_id == load.id)) or 0
    version = LoadVersion(load_id=load.id, version=number + 1, user_id=user.id, action=action, snapshot=json.dumps(load_snapshot(load), default=str, ensure_ascii=False), reason=reason)
    db.add(version)
    return version


@router.get("/loads/{load_id}", tags=["loads"])
def load_detail(load_id: UUID, _: CurrentUser, db: Database):
    load = db.get(Load, load_id)
    if not load:
        raise HTTPException(404, "Carga não encontrada")
    versions = list(db.scalars(select(LoadVersion).where(LoadVersion.load_id == load_id).order_by(LoadVersion.version.desc())))
    return {"load": load_snapshot(load), "versions": [{"id": v.id, "version": v.version, "action": v.action, "snapshot": json.loads(v.snapshot), "reason": v.reason, "created_at": v.created_at} for v in versions]}


class CancelBody(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


@router.post("/loads/{load_id}/cancel", tags=["loads"])
def cancel_load(load_id: UUID, body: CancelBody, user: Writer, db: Database):
    load = db.scalar(select(Load).where(Load.id == load_id).with_for_update())
    if not load:
        raise HTTPException(404, "Carga não encontrada")
    active_trip = db.scalar(select(Trip.id).where(Trip.load_id == load_id, Trip.status.in_([TripStatus.PLANNED, TripStatus.IN_PROGRESS])))
    if active_trip:
        raise HTTPException(409, "Cancele a viagem ativa antes de cancelar a carga")
    if load.status == LoadStatus.CANCELLED:
        raise HTTPException(409, "Carga já cancelada")
    save_version(db, load, user, "BEFORE_CANCEL", body.reason)
    load.status = LoadStatus.CANCELLED
    load.notes = f"{load.notes + ' · ' if load.notes else ''}Cancelamento: {body.reason}"
    reconcile(db, load)
    record_audit(db, user_id=user.id, action="LOAD_CANCELLED", entity_type="loads", entity_id=str(load.id), details={"reason": body.reason})
    db.commit()
    return load_snapshot(load)


@router.get("/trips/{trip_id}", tags=["trips"])
def trip_detail(trip_id: UUID, _: CurrentUser, db: Database):
    trip = db.scalar(select(Trip).where(Trip.id == trip_id).options(selectinload(Trip.load), selectinload(Trip.vehicle), selectinload(Trip.driver)))
    if not trip:
        raise HTTPException(404, "Viagem não encontrada")
    return trip


@router.get("/reports/trips", tags=["reports"])
def trip_report(_: CurrentUser, db: Database, start_date: Annotated[date | None, Query()] = None, end_date: Annotated[date | None, Query()] = None):
    query = select(Trip).options(selectinload(Trip.load), selectinload(Trip.vehicle), selectinload(Trip.driver)).order_by(Trip.scheduled_at.desc())
    if start_date:
        query = query.where(func.date(Trip.scheduled_at) >= start_date)
    if end_date:
        query = query.where(func.date(Trip.scheduled_at) <= end_date)
    return list(db.scalars(query))


class RuleSetBody(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class RuleVersionBody(BaseModel):
    version: int = Field(gt=0)
    valid_from: date
    valid_until: date | None = None
    rate_per_km: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    is_active: bool = False

    @model_validator(mode="after")
    def valid_period(self):
        if self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("Vigência final anterior à inicial")
        return self


class RuleVersionUpdate(BaseModel):
    valid_from: date
    valid_until: date | None = None
    rate_per_km: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    is_active: bool = False


@router.get("/freight-tables", tags=["freight"])
def freight_tables(_: CurrentUser, db: Database):
    sets = list(db.scalars(select(FreightRuleSet).order_by(FreightRuleSet.name)))
    versions = list(db.scalars(select(FreightRuleVersion).order_by(FreightRuleVersion.valid_from.desc())))
    return [{"id": item.id, "name": item.name, "is_active": item.is_active, "versions": [{"id": v.id, "version": v.version, "valid_from": v.valid_from, "valid_until": v.valid_until, "configuration": json.loads(v.configuration), "is_active": v.is_active} for v in versions if v.rule_set_id == item.id]} for item in sets]


@router.post("/freight-tables", status_code=201, tags=["freight"])
def create_freight_table(body: RuleSetBody, user: Manager, db: Database):
    item = FreightRuleSet(name=body.name)
    db.add(item)
    db.flush()
    record_audit(db, user_id=user.id, action="FREIGHT_TABLE_CREATED", entity_type="freight_rule_sets", entity_id=str(item.id), details=body.model_dump())
    db.commit()
    db.refresh(item)
    return item


@router.post("/freight-tables/{table_id}/versions", status_code=201, tags=["freight"])
def create_rule_version(table_id: UUID, body: RuleVersionBody, user: Manager, db: Database):
    if not db.get(FreightRuleSet, table_id):
        raise HTTPException(404, "Tabela de frete não encontrada")
    if body.is_active:
        for current in db.scalars(select(FreightRuleVersion).where(FreightRuleVersion.rule_set_id == table_id)):
            current.is_active = False
    version = FreightRuleVersion(rule_set_id=table_id, version=body.version, valid_from=body.valid_from, valid_until=body.valid_until, configuration=json.dumps({"rate_per_km": str(body.rate_per_km)}), is_active=body.is_active)
    db.add(version)
    db.flush()
    record_audit(db, user_id=user.id, action="FREIGHT_TABLE_VERSION_CREATED", entity_type="freight_rule_versions", entity_id=str(version.id), details=body.model_dump())
    db.commit()
    db.refresh(version)
    return version


@router.patch("/freight-tables/{table_id}/versions/{version_id}", tags=["freight"])
def update_rule_version(table_id: UUID, version_id: UUID, body: RuleVersionUpdate, user: Manager, db: Database):
    version = db.scalar(select(FreightRuleVersion).where(FreightRuleVersion.id == version_id, FreightRuleVersion.rule_set_id == table_id).with_for_update())
    if not version:
        raise HTTPException(404, "Versão da tabela não encontrada")
    if body.valid_until and body.valid_until < body.valid_from:
        raise HTTPException(422, "Vigência final anterior à inicial")
    if body.is_active:
        for current in db.scalars(select(FreightRuleVersion).where(FreightRuleVersion.rule_set_id == table_id, FreightRuleVersion.id != version_id)):
            current.is_active = False
    before = {"valid_from": version.valid_from, "valid_until": version.valid_until, "configuration": version.configuration, "is_active": version.is_active}
    version.valid_from = body.valid_from
    version.valid_until = body.valid_until
    version.configuration = json.dumps({"rate_per_km": str(body.rate_per_km)})
    version.is_active = body.is_active
    record_audit(db, user_id=user.id, action="FREIGHT_TABLE_VERSION_UPDATED", entity_type="freight_rule_versions", entity_id=str(version.id), details={"before": before, "after": body.model_dump()})
    db.commit()
    db.refresh(version)
    return version


@router.post("/loads/{load_id}/calculate-freight", status_code=201, tags=["freight"])
def calculate_freight(load_id: UUID, user: Manager, db: Database):
    load = db.get(Load, load_id)
    if not load or load.distance_km is None:
        raise HTTPException(422, "Carga sem distância para cálculo")
    calculation_date = load.pickup_date or datetime.now(UTC).date()
    version = db.scalar(select(FreightRuleVersion).where(FreightRuleVersion.is_active.is_(True), FreightRuleVersion.valid_from <= calculation_date, (FreightRuleVersion.valid_until.is_(None) | (FreightRuleVersion.valid_until >= calculation_date))).order_by(FreightRuleVersion.valid_from.desc()).limit(1))
    if not version:
        raise HTTPException(422, "Não há versão ativa da tabela para a data da carga")
    try:
        rate = Decimal(json.loads(version.configuration)["rate_per_km"])
    except (KeyError, InvalidOperation, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "Versão da tabela sem tarifa estruturada válida") from exc
    amount = (load.distance_km * rate).quantize(Decimal("0.01"))
    snapshot = {"distance_km": str(load.distance_km), "rate_per_km": str(rate), "pickup_date": str(calculation_date)}
    calculation = FreightCalculation(load_id=load.id, rule_version_id=version.id, user_id=user.id, input_snapshot=json.dumps(snapshot), amount=amount, explanation="Distância × tarifa por km da versão vigente")
    db.add(calculation)
    db.flush()
    record_audit(db, user_id=user.id, action="FREIGHT_CALCULATED", entity_type="freight_calculations", entity_id=str(calculation.id), details={**snapshot, "amount": amount, "rule_version_id": version.id})
    db.commit()
    return {"id": calculation.id, "load_id": load.id, "rule_version_id": version.id, "input": snapshot, "amount": amount, "explanation": calculation.explanation, "created_at": calculation.created_at}


@router.get("/integrations/health", tags=["integrations"])
def integrations_health(_: CurrentUser):
    return {"gps": {"provider": settings.gps_provider, "status": "OPERACIONAL" if settings.gps_provider == "mock" else "CONFIGURADO", "retry_supported": True}, "copagril": {"provider": "UPLOAD_MANUAL", "status": "OPERACIONAL", "retry_supported": False}, "whatsapp": {"status": "FORA_DO_ESCOPO", "reason": "Decisão aprovada por custo"}}


@router.post("/integrations/{integration_id}/retry", tags=["integrations"])
def retry_integration(integration_id: str, user: Writer, db: Database):
    if integration_id != "gps-mock":
        raise HTTPException(404, "Evento de integração não encontrado ou sem retry")
    record_audit(db, user_id=user.id, action="INTEGRATION_RETRY", entity_type="integrations", entity_id=integration_id, details={"provider": settings.gps_provider, "result": "OK"})
    db.commit()
    return {"integration_id": integration_id, "status": "REPROCESSADO", "provider": settings.gps_provider}
