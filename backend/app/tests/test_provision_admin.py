from sqlalchemy import select

from app.core.security import verify_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.provision_admin import provision_admin


def test_provision_admin_creates_and_updates_account(monkeypatch):
    email = "teste.admin@transboes.com.br"
    monkeypatch.setenv("PROVISION_ADMIN_EMAIL", email)
    monkeypatch.setenv("PROVISION_ADMIN_PASSWORD", "PrimeiraSenhaForte!2026")
    provision_admin()

    monkeypatch.setenv("PROVISION_ADMIN_PASSWORD", "SegundaSenhaForte!2026")
    provision_admin()

    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email == email)).all()
        assert len(users) == 1
        assert users[0].role == UserRole.ADMIN
        assert users[0].is_active is True
        assert verify_password("SegundaSenhaForte!2026", users[0].password_hash)
