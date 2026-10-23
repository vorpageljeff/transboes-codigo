from decimal import Decimal

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.freight import FreightValidationStatus
from app.models.user import User, UserRole
from app.modules.freight.engine import ConfigurableFreightValidationEngine
from app.tests.test_operations import auth_headers


def create_financial_fixture(client, headers):
    vehicle = client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={"plate": "FIN1A23", "model": "Modelo financeiro", "capacity_kg": 30000},
    ).json()
    load = client.post(
        "/api/v1/loads",
        headers=headers,
        json={
            "reference": "FIN-001",
            "customer": "Frimesa",
            "product": "Suínos",
            "origin": "Produtor A",
            "destination": "UFM",
            "weight_kg": 25000,
            "freight_value": 5000,
            "pickup_date": "2026-09-08",
        },
    ).json()
    return vehicle, load


def test_financial_summary_validation_and_csv(client):
    headers = auth_headers(client)
    vehicle, load = create_financial_fixture(client, headers)
    cost = client.post(
        "/api/v1/financial/costs",
        headers=headers,
        json={
            "vehicle_id": vehicle["id"],
            "category": "COMBUSTIVEL",
            "amount": 1200,
            "incurred_on": "2026-09-08",
            "description": "Abastecimento",
        },
    )
    assert cost.status_code == 201
    validation = client.post(
        f"/api/v1/freight/loads/{load['id']}/validate", headers=headers, json={}
    )
    assert validation.status_code == 201
    assert validation.json()["status"] == "AGUARDANDO_REGRA"
    summary = client.get(
        "/api/v1/financial/summary?start_date=2026-09-01&end_date=2026-09-30",
        headers=headers,
    ).json()
    assert Decimal(summary["revenue"]) == Decimal(5000)
    assert Decimal(summary["costs"]) == Decimal(1200)
    assert Decimal(summary["estimated_margin"]) == Decimal(3800)
    report = client.get(
        "/api/v1/reports/billing.csv?start_date=2026-09-01&end_date=2026-09-30",
        headers=headers,
    )
    assert report.status_code == 200
    assert "FIN-001" in report.text


def test_manual_engine_detects_difference_without_inventing_rule():
    result = ConfigurableFreightValidationEngine("MANUAL").validate(Decimal(5000), Decimal(4800))
    assert result.status == FreightValidationStatus.DIVERGENT
    assert result.difference == Decimal(200)


def test_financial_write_rejects_operator(client):
    manager_headers = auth_headers(client)
    vehicle, _ = create_financial_fixture(client, manager_headers)
    with SessionLocal.begin() as db:
        db.add(
            User(
                name="Operador",
                email="operador@transboes.com.br",
                password_hash=hash_password("Senha123!"),
                role=UserRole.OPERATOR,
            )
        )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "operador@transboes.com.br", "password": "Senha123!"},
    ).json()
    response = client.post(
        "/api/v1/financial/costs",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={
            "vehicle_id": vehicle["id"],
            "category": "OUTRO",
            "amount": 10,
            "incurred_on": "2026-09-08",
            "description": "Teste sem permissão",
        },
    )
    assert response.status_code == 403
