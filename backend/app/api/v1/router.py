import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies import CurrentUser, Database, oauth2_scheme, require_roles
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.driver import Driver
from app.models.financial import RevenueEntry
from app.models.load import Load, LoadStatus
from app.models.load_version import LoadVersion
from app.models.session import RevokedSession
from app.models.trip import Trip, TripStatus
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle, VehicleStatus
from app.modules.audit.service import record_audit
from app.modules.auth.service import authenticate
from app.schemas.auth import (
    LoginRequest,
    ProfileUpdate,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.schemas.operations import (
    DashboardResponse,
    DriverCreate,
    DriverResponse,
    DriverUpdate,
    LoadCreate,
    LoadResponse,
    LoadUpdate,
    TripCreate,
    TripResponse,
    TripStatusUpdate,
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
)

router = APIRouter()
Writer = Annotated[
    User, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR))
]
Administrator = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
ACTIVE = (TripStatus.PLANNED, TripStatus.IN_PROGRESS)


def locked(db, model, identity):
    return db.scalar(select(model).where(model.id == identity).with_for_update())


def active_for(db, field, identity):
    return db.scalar(select(Trip.id).where(field == identity, Trip.status.in_(ACTIVE)).limit(1))


def audit(db, user, action, entity, details=None):
    db.flush()
    record_audit(
        db,
        user_id=user.id,
        action=action,
        entity_type=entity.__tablename__,
        entity_id=str(entity.id), details=details,
    )


def reconcile(db, load):
    entry = db.scalar(select(RevenueEntry).where(RevenueEntry.load_id == load.id))
    if load.freight_value is None or load.status == LoadStatus.CANCELLED:
        if entry:
            db.delete(entry)
        return
    if entry is None:
        entry = RevenueEntry(load_id=load.id)
        db.add(entry)
    entry.amount = load.freight_value
    entry.recognized_on = load.pickup_date or load.created_at.date()


def preserve_load_version(db, load, user, action, reason=None):
    number = db.scalar(
        select(func.max(LoadVersion.version)).where(LoadVersion.load_id == load.id)
    ) or 0
    snapshot = {column.name: getattr(load, column.name) for column in load.__table__.columns}
    db.add(
        LoadVersion(
            load_id=load.id,
            version=number + 1,
            user_id=user.id,
            action=action,
            snapshot=json.dumps(snapshot, default=str, ensure_ascii=False),
            reason=reason,
        )
    )


def user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest, db: Database) -> TokenResponse:
    user = authenticate(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos"
        )
    return TokenResponse(
        access_token=create_access_token(
            str(user.id), user.role.value, user.session_version
        ),
        user=user_response(user),
    )


@router.get("/auth/me", response_model=UserResponse, tags=["auth"])
def me(user: CurrentUser) -> UserResponse:
    return user_response(user)


@router.patch("/auth/me", response_model=UserResponse, tags=["auth"])
def update_profile(body: ProfileUpdate, user: CurrentUser, db: Database) -> UserResponse:
    if (body.email or body.new_password) and not verify_password(
        body.current_password or "", user.password_hash
    ):
        raise HTTPException(status_code=403, detail="Senha atual incorreta")
    if body.email:
        email = str(body.email).lower()
        owner = db.scalar(select(User).where(User.email == email, User.id != user.id))
        if owner:
            raise _conflict("Este e-mail já está em uso")
        user.email = email
    if body.name:
        user.name = body.name.strip()
    password_changed = bool(body.new_password)
    if body.new_password:
        user.password_hash = hash_password(body.new_password)
        user.session_version += 1
    audit(
        db,
        user,
        "PROFILE_UPDATED",
        user,
        {
            "name_changed": bool(body.name),
            "email_changed": bool(body.email),
            "password_changed": password_changed,
        },
    )
    db.commit()
    db.refresh(user)
    return user_response(user)


@router.get("/users", response_model=list[UserResponse], tags=["users"])
def list_users(_: Administrator, db: Database) -> list[User]:
    return list(db.scalars(select(User).order_by(User.name, User.email)))


@router.post("/users", response_model=UserResponse, status_code=201, tags=["users"])
def create_user(body: UserCreate, administrator: Administrator, db: Database) -> UserResponse:
    user = User(
        name=body.name.strip(),
        email=str(body.email).lower(),
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    try:
        audit(
            db,
            administrator,
            "USER_CREATED",
            user,
            {"email": user.email, "role": user.role.value},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _conflict("Este e-mail já está em uso") from None
    db.refresh(user)
    return user_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse, tags=["users"])
def update_user(
    user_id: UUID, body: UserUpdate, administrator: Administrator, db: Database
) -> UserResponse:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise _not_found("Usuário")
    if user.id == administrator.id and (
        body.is_active is False or (body.role is not None and body.role != UserRole.ADMIN)
    ):
        raise _conflict("Você não pode remover o próprio acesso administrativo")
    removing_admin = user.role == UserRole.ADMIN and (
        body.is_active is False or (body.role is not None and body.role != UserRole.ADMIN)
    )
    if removing_admin:
        active_admins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
        if (active_admins or 0) <= 1:
            raise _conflict("O sistema precisa manter pelo menos um administrador ativo")
    changes = body.model_dump(exclude_unset=True, exclude={"password"})
    if body.name is not None:
        user.name = body.name.strip()
    if body.email is not None:
        user.email = str(body.email).lower()
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)
        user.session_version += 1
        changes["password_changed"] = True
    try:
        audit(db, administrator, "USER_UPDATED", user, changes)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _conflict("Este e-mail já está em uso") from None
    db.refresh(user)
    return user_response(user)


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} não encontrado")


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail=message)


@router.get("/dashboard", response_model=DashboardResponse, tags=["operations"])
def dashboard(_: CurrentUser, db: Database) -> DashboardResponse:
    return DashboardResponse(
        pending_loads=db.scalar(
            select(func.count()).select_from(Load).where(Load.status == LoadStatus.PENDING)
        )
        or 0,
        available_vehicles=db.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(Vehicle.status == VehicleStatus.AVAILABLE)
        )
        or 0,
        active_trips=db.scalar(
            select(func.count()).select_from(Trip).where(Trip.status == TripStatus.IN_PROGRESS)
        )
        or 0,
        occurrences=0,
    )


@router.get("/vehicles", response_model=list[VehicleResponse], tags=["fleet"])
def list_vehicles(_: CurrentUser, db: Database) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).order_by(Vehicle.plate)))


@router.post("/vehicles", response_model=VehicleResponse, status_code=201, tags=["fleet"])
def create_vehicle(body: VehicleCreate, user: Writer, db: Database) -> Vehicle:
    values = body.model_dump()
    values["plate"] = body.plate.upper().replace("-", "")
    vehicle = Vehicle(**values)
    db.add(vehicle)
    try:
        audit(db, user, "VEHICLE_CREATED", vehicle)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _conflict("Já existe um veículo com esta placa") from None
    db.refresh(vehicle)
    return vehicle


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleResponse, tags=["fleet"])
def update_vehicle(vehicle_id: UUID, body: VehicleUpdate, user: Writer, db: Database) -> Vehicle:
    vehicle = locked(db, Vehicle, vehicle_id)
    if not vehicle:
        raise _not_found("Veículo")
    if active_for(db, Trip.vehicle_id, vehicle_id):
        raise _conflict("Recurso reservado: finalize ou cancele a viagem antes de editar")
    if body.status is not None and body.status not in {VehicleStatus.AVAILABLE, VehicleStatus.MAINTENANCE, VehicleStatus.INACTIVE}:
        raise _conflict("Status de viagem é controlado pela programação")
    changes = body.model_dump(exclude_unset=True)
    before = {key: getattr(vehicle, key) for key in changes}
    for key, value in changes.items():
        setattr(vehicle, key, value)
    audit(db, user, "VEHICLE_UPDATED", vehicle, {"before": before, "after": changes})
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/drivers", response_model=list[DriverResponse], tags=["fleet"])
def list_drivers(_: CurrentUser, db: Database) -> list[Driver]:
    return list(db.scalars(select(Driver).order_by(Driver.name)))


@router.post("/drivers", response_model=DriverResponse, status_code=201, tags=["fleet"])
def create_driver(body: DriverCreate, user: Writer, db: Database) -> Driver:
    driver = Driver(**body.model_dump())
    db.add(driver)
    try:
        audit(db, user, "DRIVER_CREATED", driver)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _conflict("Já existe um motorista com esta CNH") from None
    db.refresh(driver)
    return driver


@router.patch("/drivers/{driver_id}", response_model=DriverResponse, tags=["fleet"])
def update_driver(driver_id: UUID, body: DriverUpdate, user: Writer, db: Database) -> Driver:
    driver = locked(db, Driver, driver_id)
    if not driver:
        raise _not_found("Motorista")
    if active_for(db, Trip.driver_id, driver_id):
        raise _conflict("Recurso reservado: finalize ou cancele a viagem antes de editar")
    changes = body.model_dump(exclude_unset=True)
    before = {key: getattr(driver, key) for key in changes}
    for key, value in changes.items():
        setattr(driver, key, value)
    audit(db, user, "DRIVER_UPDATED", driver, {"before": before, "after": changes})
    db.commit()
    db.refresh(driver)
    return driver


@router.get("/loads", response_model=list[LoadResponse], tags=["loads"])
def list_loads(_: CurrentUser, db: Database) -> list[Load]:
    return list(db.scalars(select(Load).order_by(Load.created_at.desc())))


@router.post("/loads", response_model=LoadResponse, status_code=201, tags=["loads"])
def create_load(body: LoadCreate, user: Writer, db: Database) -> Load:
    load = Load(**body.model_dump())
    db.add(load)
    try:
        db.flush()
        if load.freight_value is not None:
            db.add(
                RevenueEntry(
                    load_id=load.id,
                    amount=load.freight_value,
                    recognized_on=load.pickup_date or datetime.now(UTC).date(),
                )
            )
        audit(db, user, "LOAD_CREATED", load)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _conflict("Já existe uma carga com esta referência") from None
    db.refresh(load)
    return load


@router.patch("/loads/{load_id}", response_model=LoadResponse, tags=["loads"])
def update_load(load_id: UUID, body: LoadUpdate, user: Writer, db: Database) -> Load:
    load = locked(db, Load, load_id)
    if not load:
        raise _not_found("Carga")
    if active_for(db, Trip.load_id, load_id):
        raise _conflict("Recurso reservado: finalize ou cancele a viagem antes de editar")
    if body.status is not None and body.status != load.status:
        allowed = {LoadStatus.PENDING: {LoadStatus.CANCELLED}, LoadStatus.CANCELLED: {LoadStatus.PENDING}}
        if body.status not in allowed.get(load.status, set()):
            raise _conflict("Status da carga deve acompanhar a viagem")
    changes = body.model_dump(exclude_unset=True)
    before = {key: getattr(load, key) for key in changes}
    preserve_load_version(db, load, user, "BEFORE_UPDATE", body.notes)
    for key, value in changes.items():
        setattr(load, key, value)
    reconcile(db, load)
    audit(db, user, "LOAD_UPDATED", load, {"before": before, "after": changes})
    db.commit()
    db.refresh(load)
    return load


@router.get("/trips", response_model=list[TripResponse], tags=["trips"])
def list_trips(_: CurrentUser, db: Database) -> list[Trip]:
    query = (
        select(Trip)
        .options(selectinload(Trip.load), selectinload(Trip.vehicle), selectinload(Trip.driver))
        .order_by(Trip.scheduled_at.desc())
    )
    return list(db.scalars(query))


@router.post("/trips", response_model=TripResponse, status_code=201, tags=["trips"])
def create_trip(body: TripCreate, user: Writer, db: Database) -> Trip:
    load = locked(db, Load, body.load_id)
    vehicle = locked(db, Vehicle, body.vehicle_id)
    driver = locked(db, Driver, body.driver_id)
    if not load or not vehicle or not driver:
        raise HTTPException(status_code=422, detail="Carga, veículo ou motorista inválido")
    if load.status != LoadStatus.PENDING:
        raise _conflict("A carga não está disponível para programação")
    if vehicle.status != VehicleStatus.AVAILABLE or not driver.is_active:
        raise _conflict("Veículo ou motorista indisponível")
    if active_for(db, Trip.driver_id, driver.id):
        raise _conflict("Motorista já reservado em outra viagem")
    if ((vehicle.maintenance_due_km is not None and vehicle.odometer_km >= vehicle.maintenance_due_km)
        or (vehicle.maintenance_due_on is not None and vehicle.maintenance_due_on <= datetime.now(UTC).date())):
        raise _conflict("Veículo com manutenção vencida")
    if load.weight_kg > vehicle.capacity_kg:
        raise _conflict("A carga excede a capacidade do veículo")
    trip = Trip(**body.model_dump())
    load.status = LoadStatus.SCHEDULED
    vehicle.status = VehicleStatus.RESERVED
    db.add(trip)
    audit(db, user, "TRIP_CREATED", trip)
    db.commit()
    return db.scalar(
        select(Trip)
        .where(Trip.id == trip.id)
        .options(selectinload(Trip.load), selectinload(Trip.vehicle), selectinload(Trip.driver))
    )


def apply_trip_status(trip_id: UUID, body: TripStatusUpdate, user: Writer, db: Database) -> Trip:
    trip = db.scalar(
        select(Trip)
        .where(Trip.id == trip_id)
        .with_for_update()
        .options(selectinload(Trip.load), selectinload(Trip.vehicle), selectinload(Trip.driver))
    )
    if not trip:
        raise _not_found("Viagem")
    allowed = {
        TripStatus.PLANNED: {TripStatus.IN_PROGRESS, TripStatus.CANCELLED},
        TripStatus.IN_PROGRESS: {TripStatus.COMPLETED, TripStatus.CANCELLED},
    }
    if body.status not in allowed.get(trip.status, set()):
        raise _conflict("Mudança de status não permitida")
    now = datetime.now(UTC)
    trip.status = body.status
    if body.status == TripStatus.IN_PROGRESS:
        trip.started_at = now
        trip.load.status = LoadStatus.IN_TRANSIT
        trip.vehicle.status = VehicleStatus.ON_ROUTE
    elif body.status == TripStatus.COMPLETED:
        trip.completed_at = now
        trip.load.status = LoadStatus.DELIVERED
        trip.vehicle.status = (VehicleStatus.AVAILABLE if settings.auto_release_vehicle and settings.vehicle_release_rule == "AFTER_UNLOAD" else VehicleStatus.RETURNING)
    else:
        trip.load.status = LoadStatus.PENDING
        trip.vehicle.status = VehicleStatus.AVAILABLE
    audit(db, user, "TRIP_STATUS_CHANGED", trip)
    return trip


@router.post("/auth/logout")
def logout(user: CurrentUser, db: Database, token: Annotated[str, Depends(oauth2_scheme)]):
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    db.add(RevokedSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=datetime.fromtimestamp(payload["exp"], UTC)))
    record_audit(db, user_id=user.id, action="LOGOUT", entity_type="users", entity_id=str(user.id))
    db.commit()
    return {"status": "ok"}


@router.patch("/trips/{trip_id}/status", response_model=TripResponse, tags=["trips"])
def update_trip_status(trip_id: UUID, body: TripStatusUpdate, user: Writer, db: Database):
    trip = apply_trip_status(trip_id, body, user, db)
    db.commit()
    db.refresh(trip)
    return trip
