from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User, UserRole


def admin_headers(client):
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.email == "gestor@transboes.com.br"))
        user.role = UserRole.ADMIN
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "gestor@transboes.com.br", "password": "Senha123!"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_manages_employee_access(client):
    headers = admin_headers(client)
    created = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "name": "Funcionário Teste",
            "email": "funcionario@transboes.com.br",
            "password": "SenhaInicial123!",
            "role": "OPERATOR",
        },
    )
    assert created.status_code == 201
    employee = created.json()
    assert employee["role"] == "OPERATOR"
    assert employee["is_active"] is True
    assert "password" not in employee

    users = client.get("/api/v1/users", headers=headers)
    assert users.status_code == 200
    assert {user["email"] for user in users.json()} == {
        "gestor@transboes.com.br",
        "funcionario@transboes.com.br",
    }

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "funcionario@transboes.com.br", "password": "SenhaInicial123!"},
    )
    assert login.status_code == 200
    employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    changed = client.patch(
        f"/api/v1/users/{employee['id']}",
        headers=headers,
        json={"role": "FINANCIAL", "password": "NovaSenha123!"},
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "FINANCIAL"
    assert client.get("/api/v1/auth/me", headers=employee_headers).status_code == 401

    disabled = client.patch(
        f"/api/v1/users/{employee['id']}", headers=headers, json={"is_active": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "funcionario@transboes.com.br", "password": "NovaSenha123!"},
        ).status_code
        == 401
    )


def test_non_admin_cannot_manage_users(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "gestor@transboes.com.br", "password": "Senha123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/users", headers=headers).status_code == 403


def test_user_updates_own_profile_and_password(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "gestor@transboes.com.br", "password": "Senha123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "name": "Boes",
            "email": "boes@transboes.com.br",
            "current_password": "Senha123!",
            "new_password": "MinhaNovaSenha123!",
        },
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Boes"
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "boes@transboes.com.br", "password": "MinhaNovaSenha123!"},
        ).status_code
        == 200
    )


def test_admin_cannot_disable_own_account(client):
    headers = admin_headers(client)
    profile = client.get("/api/v1/auth/me", headers=headers).json()
    response = client.patch(
        f"/api/v1/users/{profile['id']}", headers=headers, json={"is_active": False}
    )
    assert response.status_code == 409
