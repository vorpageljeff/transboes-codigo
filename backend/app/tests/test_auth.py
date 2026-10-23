from app.core.config import Settings


def test_settings_accept_comma_separated_cors(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com,https://admin.example.com")
    configured = Settings(_env_file=None)
    assert configured.cors_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_login_and_authenticated_profile(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "gestor@transboes.com.br", "password": "Senha123!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "MANAGER"
    profile = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "gestor@transboes.com.br"


def test_login_rejects_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "gestor@transboes.com.br", "password": "errada"}
    )
    assert response.status_code == 401


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
