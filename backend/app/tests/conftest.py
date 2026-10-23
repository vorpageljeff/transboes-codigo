import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-with-at-least-thirty-two-characters"

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
def database():
    from app.core.request_limits import _attempts
    _attempts.clear()
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        db.add(
            User(
                name="Gestor Teste",
                email="gestor@transboes.com.br",
                password_hash=hash_password("Senha123!"),
                role=UserRole.MANAGER,
            )
        )
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)
