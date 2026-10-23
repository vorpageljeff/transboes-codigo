def auth_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "gestor@transboes.com.br", "password": "Senha123!"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_complete_operational_flow(client):
    headers = auth_headers(client)
    vehicle = client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={"plate": "abc-1d23", "model": "Scania R450", "capacity_kg": 36000},
    )
    assert vehicle.status_code == 201
    assert vehicle.json()["plate"] == "ABC1D23"
    driver = client.post(
        "/api/v1/drivers",
        headers=headers,
        json={"name": "Maria Silva", "license_number": "CNH-123", "phone": "44999999999"},
    )
    assert driver.status_code == 201
    load = client.post(
        "/api/v1/loads",
        headers=headers,
        json={
            "reference": "CG-1001",
            "customer": "Copagril",
            "product": "Soja",
            "origin": "Marechal Cândido Rondon",
            "destination": "Cascavel",
            "weight_kg": 32000,
            "freight_value": 4800,
        },
    )
    assert load.status_code == 201
    trip = client.post(
        "/api/v1/trips",
        headers=headers,
        json={
            "load_id": load.json()["id"],
            "vehicle_id": vehicle.json()["id"],
            "driver_id": driver.json()["id"],
            "scheduled_at": "2026-09-08T08:00:00Z",
        },
    )
    assert trip.status_code == 201
    assert trip.json()["status"] == "PLANEJADA"
    started = client.patch(
        f"/api/v1/trips/{trip.json()['id']}/status",
        headers=headers,
        json={"status": "EM_ANDAMENTO"},
    )
    assert started.status_code == 200
    assert started.json()["load"]["status"] == "EM_TRANSITO"
    completed = client.patch(
        f"/api/v1/trips/{trip.json()['id']}/status",
        headers=headers,
        json={"status": "CONCLUIDA"},
    )
    assert completed.status_code == 200
    assert completed.json()["vehicle"]["status"] == "DISPONIVEL"
    metrics = client.get("/api/v1/dashboard", headers=headers).json()
    assert metrics == {
        "pending_loads": 0,
        "available_vehicles": 1,
        "active_trips": 0,
        "occurrences": 0,
    }


def test_trip_rejects_overweight_load(client):
    headers = auth_headers(client)
    vehicle = client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={"plate": "DEF4G56", "model": "Volvo FH", "capacity_kg": 10000},
    ).json()
    driver = client.post(
        "/api/v1/drivers",
        headers=headers,
        json={"name": "João Souza", "license_number": "CNH-456"},
    ).json()
    load = client.post(
        "/api/v1/loads",
        headers=headers,
        json={
            "reference": "CG-OVER",
            "customer": "Copagril",
            "product": "Milho",
            "origin": "Toledo",
            "destination": "Cascavel",
            "weight_kg": 12000,
        },
    ).json()
    response = client.post(
        "/api/v1/trips",
        headers=headers,
        json={
            "load_id": load["id"],
            "vehicle_id": vehicle["id"],
            "driver_id": driver["id"],
            "scheduled_at": "2026-09-08T08:00:00Z",
        },
    )
    assert response.status_code == 409
    assert "capacidade" in response.json()["detail"]
