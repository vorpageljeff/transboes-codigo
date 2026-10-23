from datetime import UTC, datetime


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "gestor@transboes.com.br", "password": "Senha123!"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_load(client, headers, reference="HIST-1"):
    return client.post(
        "/api/v1/loads",
        headers=headers,
        json={
            "reference": reference,
            "customer": "Cliente",
            "product": "Suínos",
            "origin": "Origem",
            "destination": "Destino",
            "weight_kg": "1000",
            "distance_km": "120",
            "pickup_date": str(datetime.now(UTC).date()),
        },
    )


def test_locations_load_history_details_and_cancel(client):
    headers = login(client)
    location = client.post(
        "/api/v1/locations",
        headers=headers,
        json={"name": "Unidade Frimesa", "kind": "UNIDADE", "latitude": -24.1, "longitude": -53.2},
    )
    assert location.status_code == 201
    assert len(client.get("/api/v1/locations", headers=headers).json()) == 1

    load = create_load(client, headers).json()
    update = client.patch(
        f"/api/v1/loads/{load['id']}", headers=headers, json={"notes": "Retificação registrada"}
    )
    assert update.status_code == 200
    detail = client.get(f"/api/v1/loads/{load['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["versions"][0]["action"] == "BEFORE_UPDATE"
    cancel = client.post(
        f"/api/v1/loads/{load['id']}/cancel",
        headers=headers,
        json={"reason": "Cancelada pelo cliente"},
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELADA"


def test_versioned_freight_calculation_and_integration_health(client):
    headers = login(client)
    load = create_load(client, headers, "FRETE-1").json()
    table = client.post("/api/v1/freight-tables", headers=headers, json={"name": "Frimesa Oficial"})
    assert table.status_code == 201
    version = client.post(
        f"/api/v1/freight-tables/{table.json()['id']}/versions",
        headers=headers,
        json={"version": 1, "valid_from": str(datetime.now(UTC).date()), "rate_per_km": "4.25", "is_active": True},
    )
    assert version.status_code == 201
    calculation = client.post(
        f"/api/v1/loads/{load['id']}/calculate-freight", headers=headers
    )
    assert calculation.status_code == 201
    assert calculation.json()["amount"] == 510.0
    health = client.get("/api/v1/integrations/health", headers=headers)
    assert health.status_code == 200
    assert health.json()["gps"]["status"] == "OPERACIONAL"
    assert health.json()["whatsapp"]["status"] == "FORA_DO_ESCOPO"


def test_trip_events_expose_operational_indicators(client):
    headers = login(client)
    load = create_load(client, headers, "EVENT-1").json()
    vehicle = client.post("/api/v1/vehicles", headers=headers, json={"plate": "ABC1D23", "model": "Truck", "capacity_kg": 2000}).json()
    driver = client.post("/api/v1/drivers", headers=headers, json={"name": "Motorista", "license_number": "123456"}).json()
    trip = client.post("/api/v1/trips", headers=headers, json={"load_id": load["id"], "vehicle_id": vehicle["id"], "driver_id": driver["id"], "scheduled_at": "2026-09-10T12:00:00Z"}).json()
    event = client.post(f"/api/v1/trips/{trip['id']}/events", headers=headers, json={"id": "b1491124-4b6c-4311-a37c-80655c98e94c", "status": "OCORRENCIA", "note": "Parada para conferência", "occurred_at": datetime.now(UTC).isoformat(), "odometer_km": 120500, "distance_km": 35.5})
    assert event.status_code == 200
    timeline = client.get(f"/api/v1/trips/{trip['id']}/events", headers=headers)
    assert timeline.status_code == 200
    assert timeline.json()[0]["odometer_km"] == 120500
    assert timeline.json()[0]["distance_km"] == 35.5
