import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies import CurrentUser, Database
from app.api.v1.router import Writer
from app.models.tracking_share import TrackingShare
from app.models.trip import Trip, TripStatus
from app.models.vehicle import Vehicle
from app.models.vehicle_position import VehiclePosition
from app.modules.audit.service import record_audit

router = APIRouter(prefix="/tracking", tags=["tracking"])


class PositionCreate(BaseModel):
    vehicle_id: UUID
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=100000)
    speed_kmh: float | None = Field(default=None, ge=0, le=500)
    heading: float | None = Field(default=None, ge=0, lt=360)
    captured_at: AwareDatetime


class SharedPositionCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=100000)
    speed_kmh: float | None = Field(default=None, ge=0, le=500)
    heading: float | None = Field(default=None, ge=0, lt=360)
    captured_at: AwareDatetime


def position_json(position: VehiclePosition) -> dict:
    return {
        "id": position.id,
        "vehicle_id": position.vehicle_id,
        "latitude": position.latitude,
        "longitude": position.longitude,
        "accuracy_m": position.accuracy_m,
        "speed_kmh": position.speed_kmh,
        "heading": position.heading,
        "captured_at": position.captured_at,
        "source": position.source,
    }


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _validate_captured_at(value: datetime) -> datetime:
    now = datetime.now(UTC)
    captured_at = _as_utc(value)
    if captured_at > now + timedelta(minutes=5):
        raise HTTPException(422, "Data da posição está no futuro")
    if captured_at < now - timedelta(days=1):
        raise HTTPException(422, "Posição muito antiga")
    return captured_at


def _share_for_token(token: str, db: Database) -> TrackingShare:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    share = db.scalar(select(TrackingShare).where(TrackingShare.token_hash == token_hash))
    if not share:
        raise HTTPException(404, "Link de rastreamento inválido")
    if share.revoked_at or _as_utc(share.expires_at) <= datetime.now(UTC):
        raise HTTPException(410, "Este link de rastreamento expirou")
    return share


def _trip_for_share(share: TrackingShare, db: Database) -> Trip:
    trip = db.scalar(
        select(Trip)
        .where(Trip.id == share.trip_id)
        .options(selectinload(Trip.load), selectinload(Trip.vehicle), selectinload(Trip.driver))
    )
    if not trip:
        raise HTTPException(404, "Viagem não encontrada")
    if trip.status not in (TripStatus.PLANNED, TripStatus.IN_PROGRESS):
        raise HTTPException(410, "Esta viagem foi encerrada")
    return trip


@router.post("/trips/{trip_id}/shares", status_code=201)
def create_tracking_share(trip_id: UUID, user: Writer, db: Database):
    trip = db.scalar(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(selectinload(Trip.load), selectinload(Trip.vehicle), selectinload(Trip.driver))
    )
    if not trip:
        raise HTTPException(404, "Viagem não encontrada")
    if trip.status not in (TripStatus.PLANNED, TripStatus.IN_PROGRESS):
        raise HTTPException(409, "Só é possível compartilhar uma viagem ativa")
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    scheduled_at = _as_utc(trip.scheduled_at)
    expires_at = max(now + timedelta(hours=24), scheduled_at + timedelta(hours=72))
    share = TrackingShare(
        trip_id=trip.id,
        created_by_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=expires_at,
    )
    db.add(share)
    db.flush()
    record_audit(
        db,
        user_id=user.id,
        action="TRACKING_SHARE_CREATED",
        entity_type="tracking_shares",
        entity_id=str(share.id),
        details={"trip_id": trip.id, "expires_at": expires_at},
    )
    db.commit()
    return {
        "token": token,
        "expires_at": expires_at,
        "driver_name": trip.driver.name,
        "driver_phone": trip.driver.phone,
        "vehicle_plate": trip.vehicle.plate,
        "origin": trip.load.origin,
        "destination": trip.load.destination,
    }


@router.get("/share/{token}")
def shared_trip(token: str, db: Database):
    share = _share_for_token(token, db)
    trip = _trip_for_share(share, db)
    return {
        "driver_name": trip.driver.name,
        "vehicle_plate": trip.vehicle.plate,
        "vehicle_model": trip.vehicle.model,
        "load_reference": trip.load.reference,
        "origin": trip.load.origin,
        "destination": trip.load.destination,
        "scheduled_at": trip.scheduled_at,
        "status": trip.status,
        "expires_at": share.expires_at,
    }


@router.post("/share/{token}/positions", status_code=201)
def create_shared_position(token: str, body: SharedPositionCreate, db: Database):
    share = _share_for_token(token, db)
    trip = _trip_for_share(share, db)
    captured_at = _validate_captured_at(body.captured_at)
    position = VehiclePosition(
        vehicle_id=trip.vehicle_id,
        **body.model_dump(exclude={"captured_at"}),
        captured_at=captured_at,
        source="MOBILE_SHARE",
    )
    share.last_used_at = datetime.now(UTC)
    db.add(position)
    db.flush()
    record_audit(
        db,
        user_id=share.created_by_id,
        action="SHARED_VEHICLE_POSITION_RECORDED",
        entity_type="vehicle_positions",
        entity_id=str(position.id),
        details={"trip_id": trip.id, "vehicle_id": trip.vehicle_id},
        decision_source="MOBILE_SHARE",
    )
    db.commit()
    db.refresh(position)
    return position_json(position)


@router.post("/positions", status_code=201)
def create_position(body: PositionCreate, user: Writer, db: Database):
    if not db.get(Vehicle, body.vehicle_id):
        raise HTTPException(404, "Veículo não encontrado")
    captured_at = _validate_captured_at(body.captured_at)
    position = VehiclePosition(
        **body.model_dump(exclude={"captured_at"}),
        captured_at=captured_at,
        source="MOBILE_BROWSER",
    )
    db.add(position)
    db.flush()
    record_audit(
        db,
        user_id=user.id,
        action="VEHICLE_POSITION_RECORDED",
        entity_type="vehicle_positions",
        entity_id=str(position.id),
        details={"vehicle_id": body.vehicle_id, "source": position.source},
    )
    db.commit()
    db.refresh(position)
    return position_json(position)


@router.get("/positions/latest")
def latest_positions(_: CurrentUser, db: Database):
    ranked = select(
        VehiclePosition.id.label("position_id"),
        func.row_number()
        .over(
            partition_by=VehiclePosition.vehicle_id,
            order_by=(VehiclePosition.captured_at.desc(), VehiclePosition.created_at.desc()),
        )
        .label("position_rank"),
    ).subquery()
    positions = db.scalars(
        select(VehiclePosition)
        .join(ranked, ranked.c.position_id == VehiclePosition.id)
        .where(ranked.c.position_rank == 1)
        .order_by(VehiclePosition.captured_at.desc())
    )
    return [position_json(position) for position in positions]


@router.get("/vehicles/{vehicle_id}/history")
def position_history(
    vehicle_id: UUID,
    _: CurrentUser,
    db: Database,
    limit: int = Query(default=100, ge=1, le=500),
):
    if not db.get(Vehicle, vehicle_id):
        raise HTTPException(404, "Veículo não encontrado")
    positions = db.scalars(
        select(VehiclePosition)
        .where(VehiclePosition.vehicle_id == vehicle_id)
        .order_by(VehiclePosition.captured_at.desc())
        .limit(limit)
    )
    return [position_json(position) for position in positions]
from app.models.tracking_share import TrackingShare
from app.models.trip import Trip
