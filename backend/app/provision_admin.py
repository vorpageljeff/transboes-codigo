import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def provision_admin() -> None:
    email = os.environ["PROVISION_ADMIN_EMAIL"].strip().lower()
    name = os.getenv("PROVISION_ADMIN_NAME", "Administrador de Teste").strip()
    password = os.environ["PROVISION_ADMIN_PASSWORD"]
    if "@" not in email or len(password) < 16:
        raise ValueError("Informe um e-mail válido e uma senha com pelo menos 16 caracteres")

    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(name=name, email=email, password_hash="", role=UserRole.ADMIN)
            db.add(user)
        user.name = name
        user.password_hash = hash_password(password)
        user.role = UserRole.ADMIN
        user.is_active = True

    print(f"Administrador provisionado: {email}")


if __name__ == "__main__":
    provision_admin()
