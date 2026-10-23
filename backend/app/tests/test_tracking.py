from datetime import UTC, datetime


def auth_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "gestor@transboes.com.br", "password": "Senha123!"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_vehicle(client, headers):
    response = client.post(
        "/api/v1/vehicles",
        headers=headers,
        json={"plate": "GPS1A23", "model": "Caminhão de teste", "capacity_kg": 20000},
    )
    assert response.status_code == 201
    return response.json()


def create_trip(client, headers):
    vehicle = create_vehicle(client, headers)
    driver = client.post(
        "/api/v1/drivers",
        headers=headers,
        json={"name": "Motorista Teste", "license_number": "CNH-GPS", "phone": "44999999999"},
    ).json()
    load = client.post(
        "/api/v1/loads",
        headers=headers,
        json={
            "reference": "GPS-LOAD",
            "customer": "Cliente Teste",
            "product": "Soja",
            "origin": "Marechal Cândido Rondon",
            "destination": "Cascavel",
            "weight_kg": 10000,
        },
    ).json()
    trip = client.post(
        "/api/v1/trips",
        headers=headers,
        json={
            "vehicle_id": vehicle["id"],
            "driver_id": driver["id"],
            "load_id": load["id"],
            "scheduled_at": datetime.now(UTC).isoformat(),
        },
    )
    assert trip.status_code == 201
    return trip.json()


def test_mobile_position_is_recorded_and_returned(client):
    headers = auth_headers(client)
    vehicle = create_vehicle(client, headers)
    body = {
        "vehicle_id": vehicle["id"],
        "latitude": -24.556123456789,
        "longitude": -54.057987654321,
        "accuracy_m": 8.512345,
        "speed_kmh": 42.312345,
        "heading": 120.123456,
        "captured_at": datetime.now(UTC).isoformat(),
    }
    created = client.post("/api/v1/tracking/positions", headers=headers, json=body)
    assert created.status_code == 201
    assert created.json()["source"] == "MOBILE_BROWSER"

    latest = client.get("/api/v1/tracking/positions/latest", headers=headers)
    assert latest.status_code == 200
    assert latest.json()[0]["vehicle_id"] == vehicle["id"]

    history = client.get(
        f"/api/v1/tracking/vehicles/{vehicle['id']}/history", headers=headers
    )
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_mobile_position_validates_vehicle_and_coordinates(client):
    headers = auth_headers(client)
    vehicle = create_vehicle(client, headers)
    response = client.post(
        "/api/v1/tracking/positions",
        headers=headers,
        json={
            "vehicle_id": vehicle["id"],
            "latitude": 91,
            "longitude": -54,
            "captured_at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 422


def test_driver_can_share_location_with_temporary_trip_link(client):
    headers = auth_headers(client)
    trip = create_trip(client, headers)
    created = client.post(f"/api/v1/tracking/trips/{trip['id']}/shares", headers=headers)
    assert created.status_code == 201
    token = created.json()["token"]
    assert created.json()["driver_phone"] == "44999999999"

    public_trip = client.get(f"/api/v1/tracking/share/{token}")
    assert public_trip.status_code == 200
    assert public_trip.json()["vehicle_plate"] == "GPS1A23"

    position = client.post(
        f"/api/v1/tracking/share/{token}/positions",
        json={
            "latitude": -24.556123456789,
            "longitude": -54.057987654321,
            "accuracy_m": 7.1234,
            "speed_kmh": 48.7654,
            "heading": 91.2345,
            "captured_at": datetime.now(UTC).isoformat(),
        },
    )
    assert position.status_code == 201
    assert position.json()["source"] == "MOBILE_SHARE"


def test_tracking_link_stops_after_trip_is_completed(client):
    headers = auth_headers(client)
    trip = create_trip(client, headers)
    share = client.post(
        f"/api/v1/tracking/trips/{trip['id']}/shares", headers=headers
    ).json()
    client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        headers=headers,
        json={"status": "EM_ANDAMENTO"},
    )
    client.patch(
        f"/api/v1/trips/{trip['id']}/status",
        headers=headers,
        json={"status": "CONCLUIDA"},
    )
    expired = client.get(f"/api/v1/tracking/share/{share['token']}")
    assert expired.status_code == 410
