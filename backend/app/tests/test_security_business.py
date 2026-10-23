from decimal import Decimal

from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.financial import RevenueEntry
from app.models.user import User, UserRole
from app.tests.test_operations import auth_headers


def make_load(client, headers, ref="SEC"):
    return client.post(
        "/api/v1/loads",
        headers=headers,
        json={
            "reference": ref,
            "customer": "Audit",
            "product": "Audit",
            "origin": "AA",
            "destination": "BB",
            "weight_kg": 100,
            "freight_value": 100,
        },
    ).json()


def test_viewer_cannot_write(client):
    with SessionLocal.begin() as db:
        user = db.scalar(select(User))
        user.role = UserRole.VIEWER
        token = create_access_token(str(user.id), user.role.value)
    h = {"Authorization": "Bearer " + token}
    assert (
        client.post(
            "/api/v1/vehicles",
            headers=h,
            json={"plate": "AAA1234", "model": "Audit", "capacity_kg": 1000},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/loads",
            headers=h,
            json={
                "reference": "SEC",
                "customer": "Audit",
                "product": "Audit",
                "origin": "AA",
                "destination": "BB",
                "weight_kg": 100,
            },
        ).status_code
        == 403
    )


def test_revenue_reconciles(client):
    h = auth_headers(client)
    load = make_load(client, h)
    assert (
        client.patch(
            "/api/v1/loads/" + load["id"], headers=h, json={"freight_value": 200}
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert db.scalar(select(RevenueEntry)).amount == Decimal(200)
    assert (
        client.patch("/api/v1/loads/" + load["id"], headers=h, json={"customer": None}).status_code
        == 422
    )


def test_driver_reservation_and_resource_edit(client):
    h = auth_headers(client)
    driver = client.post(
        "/api/v1/drivers", headers=h, json={"name": "Audit", "license_number": "SEC123"}
    ).json()
    for i in range(2):
        load = make_load(client, h, str(i))
        vehicle = client.post(
            "/api/v1/vehicles",
            headers=h,
            json={"plate": f"AAA123{i}", "model": "Audit", "capacity_kg": 1000},
        ).json()
        r = client.post(
            "/api/v1/trips",
            headers=h,
            json={
                "load_id": load["id"],
                "vehicle_id": vehicle["id"],
                "driver_id": driver["id"],
                "scheduled_at": "2026-09-10T10:00:00Z",
            },
        )
        assert r.status_code == (201 if i == 0 else 409)
        if i == 0:
            assert (
                client.patch(
                    "/api/v1/vehicles/" + vehicle["id"], headers=h, json={"status": "DISPONIVEL"}
                ).status_code
                == 409
            )


def test_collection_requires_review_and_receipt(client):
    h = auth_headers(client)
    load = make_load(client, h)
    case = client.post(
        "/api/v1/collections",
        headers=h,
        json={
            "load_id": load["id"],
            "claim_amount": 20,
            "reason": "Diferença revisada",
            "evidence_reference": "Romaneio 123",
        },
    )
    assert case.status_code == 201
    url = "/api/v1/collections/" + case.json()["id"]
    assert (
        client.patch(
            url,
            headers=h,
            json={
                "status": "RECEBIDA",
                "note": "Recebido no banco",
                "received_amount": 20,
                "receipt_reference": "Banco 123",
            },
        ).status_code
        == 409
    )
    assert (
        client.patch(
            url, headers=h, json={"status": "COBRADA", "note": "Cobrança registrada"}
        ).status_code
        == 200
    )
    assert (
        client.patch(
            url, headers=h, json={"status": "RECEBIDA", "note": "Recebido no banco"}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            url,
            headers=h,
            json={
                "status": "RECEBIDA",
                "note": "Recebido no banco",
                "received_amount": 20,
                "receipt_reference": "Banco 123",
            },
        ).status_code
        == 200
    )
    assert (
        Decimal(str(client.get("/api/v1/business/metrics", headers=h).json()["recovered_amount"]))
        == 20
    )
    assert (
        client.post(
            "/api/v1/collections",
            headers=h,
            json={
                "load_id": load["id"],
                "claim_amount": 20,
                "reason": "Diferença revisada",
                "evidence_reference": "Romaneio 123",
            },
        ).status_code
        == 409
    )


def test_logout_revokes_token(client):
    h = auth_headers(client)
    assert client.post('/api/v1/auth/logout', headers=h).status_code == 200
    assert client.get('/api/v1/auth/me', headers=h).status_code == 401


def test_login_throttle(client):
    payload = {'email': 'nobody@example.com', 'password': 'invalid'}
    for _ in range(10):
        assert client.post('/api/v1/auth/login', json=payload).status_code == 401
    assert client.post('/api/v1/auth/login', json=payload).status_code == 429


def test_import_rejects_changed_schema(client):
    from app.tests.test_imports import report_file
    content = report_file().replace(b'Filial', b'Outra coluna')
    assert client.post('/api/v1/imports/copagril-report', headers=auth_headers(client), files={'file':('report.xls',content)}).status_code == 422


def test_mobile_event_replay_and_maintenance(client):
    from uuid import uuid4
    h=auth_headers(client)
    vehicle=client.post('/api/v1/vehicles',headers=h,json={'plate':'MOB1234','model':'Truck','capacity_kg':1000}).json()
    driver=client.post('/api/v1/drivers',headers=h,json={'name':'Mobile','license_number':'MOB123'}).json()
    load=make_load(client,h)
    trip=client.post('/api/v1/trips',headers=h,json={'load_id':load['id'],'vehicle_id':vehicle['id'],'driver_id':driver['id'],'scheduled_at':'2026-09-08T12:00:00Z'}).json()
    event={'id':str(uuid4()),'status':'EM_ANDAMENTO','note':'Saída registrada','occurred_at':'2026-09-08T12:00:00Z'}
    url='/api/v1/trips/'+trip['id']+'/events'
    assert client.post(url,headers=h,json=event).status_code==200
    assert client.post(url,headers=h,json=event).status_code==200
    assert len(client.get(url,headers=h).json())==1
    assert client.patch('/api/v1/trips/'+trip['id']+'/status',headers=h,json={'status':'CONCLUIDA'}).status_code==200
    assert client.patch('/api/v1/vehicles/'+vehicle['id'],headers=h,json={'odometer_km':1000,'maintenance_due_km':900}).status_code==200
    load2=make_load(client,h,'SECOND')
    suggested=client.get('/api/v1/planning/loads/'+load2['id']+'/suggestions',headers=h).json()
    assert suggested['vehicles']==[]
    assert client.post('/api/v1/trips',headers=h,json={'load_id':load2['id'],'vehicle_id':vehicle['id'],'driver_id':driver['id'],'scheduled_at':'2026-09-08T15:00:00Z'}).status_code==409


def test_unreserved_status_cannot_invent_trip(client):
    h=auth_headers(client)
    load=make_load(client,h)
    assert client.patch('/api/v1/loads/'+load['id'],headers=h,json={'status':'EM_TRANSITO'}).status_code==409
    vehicle=client.post('/api/v1/vehicles',headers=h,json={'plate':'SEC9999','model':'Truck','capacity_kg':1000}).json()
    assert client.patch('/api/v1/vehicles/'+vehicle['id'],headers=h,json={'status':'EM_ROTA'}).status_code==409


def test_request_body_is_bounded(client):
    response=client.post('/api/v1/auth/login',content=b'x'*(12*1024*1024+1),headers={'Content-Type':'application/json'})
    assert response.status_code==413
