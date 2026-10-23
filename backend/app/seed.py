import os
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.driver import Driver
from app.models.location import Location
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle


def seed() -> None:
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@transboes.com.br").lower()
    password = os.getenv("SEED_ADMIN_PASSWORD", "TroqueEstaSenha123!")
    with SessionLocal.begin() as db:
        if not db.scalar(select(User).where(User.email == email)):
            db.add(
                User(
                    name="Administrador",
                    email=email,
                    password_hash=hash_password(password),
                    role=UserRole.ADMIN,
                )
            )
        if not db.scalar(select(Vehicle).limit(1)):
            db.add_all(
                [
                    Vehicle(plate="ABC1D23", model="Scania R450", capacity_kg=Decimal(36000)),
                    Vehicle(plate="DEF4G56", model="Volvo FH", capacity_kg=Decimal(34000)),
                ]
            )
        if not db.scalar(select(Driver).limit(1)):
            db.add(
                Driver(
                    name="Motorista Demonstração", phone="+5544999999999", license_number="DEMO-001"
                )
            )
        if not db.scalar(select(Location).limit(1)):
            db.add(Location(name="Base Trans Boes", kind="BASE", source="seed"))
    print(f"Seed concluído. Administrador: {email}")


if __name__ == "__main__":
    seed()
