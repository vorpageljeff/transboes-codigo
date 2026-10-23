from app.tests.test_operations import auth_headers


def report_file() -> bytes:
    headers = [
        "Filial",
        "Transportador",
        "Filiada",
        "Produtor",
        "Cidade",
        "Viagem",
        "Placa Veículo",
        "Modelo Veíc.",
        "Motorista",
        "Data Recebimento",
        "N° da GTA",
        "Romaneio",
        "Lote",
        "Descrição Nota Fiscal",
        "Peso Vivo",
        "Quant.",
        "Distância",
        "R$ Frete MS Total",
        "R$ Frete Romaneiro Calculado",
    ]
    rows = [
        [
            "P51:UFR-Marechal Candido Rondon",
            "3029 - Transportadora",
            "COPAGRIL",
            "PRODUTOR TESTE",
            "PR - TOLEDO",
            "1906539",
            "BEZ5J39-PR",
            "BITRUCK",
            "MOTORISTA TESTE",
            "10/07/26 05:19",
            "356228AI",
            "440797",
            "213585",
            "20072026 - 1131026",
            "11.810,63",
            "90",
            "72",
            "940,37",
            "981,75",
        ],
        [
            "P51:UFR-Marechal Candido Rondon",
            "3029 - Transportadora",
            "COPAGRIL",
            "OUTRO PRODUTOR",
            "PR - SANTA HELENA",
            "1906540",
            "UBM3G42-PR",
            "BITRUCK",
            "OUTRO MOTORISTA",
            "11/07/26 04:00",
            "356229AI",
            "440798",
            "213586",
            "20072026 - 1131027",
            "12.000,00",
            "92",
            "96",
            "1.023,11",
            "1.023,11",
        ],
    ]
    head = "".join(f"<td>{value}</td>" for value in headers)
    body = "".join(
        "<tr>"
        + "".join(
            f'<td class="{"c66" if row_index == 0 and index == 17 else "c6"}">{value}</td>'
            for index, value in enumerate(row)
        )
        + "</tr>"
        for row_index, row in enumerate(rows)
    )
    return (
        f"<html><body><p>Relatório das Viagens de Suínos</p><table><tr>{head}</tr>{body}</table></body></html>"
    ).encode()


def test_report_import_is_idempotent_and_builds_financial_data(client):
    headers = auth_headers(client)
    content = report_file()
    response = client.post(
        "/api/v1/imports/copagril-report",
        headers=headers,
        files={"file": ("report.xls", content, "application/vnd.ms-excel")},
    )
    assert response.status_code == 201
    assert response.json()["total_rows"] == 2
    assert response.json()["imported_rows"] == 2
    detail = client.get(
        f"/api/v1/imports/{response.json()['id']}", headers=headers
    )
    assert detail.status_code == 200
    assert len(detail.json()["rows"]) == 2
    assert {row["status"] for row in detail.json()["rows"]} == {"IMPORTADA"}
    duplicate = client.post(
        "/api/v1/imports/copagril-report",
        headers=headers,
        files={"file": ("report.xls", content, "application/vnd.ms-excel")},
    )
    assert duplicate.status_code == 409
    loads = client.get("/api/v1/loads", headers=headers).json()
    assert len(loads) == 2
    assert loads[0]["distance_km"] in {"72.00", "96.00"}
    validations = client.get("/api/v1/freight/validations", headers=headers).json()
    assert {item["status"] for item in validations} == {"CONFERIDO_OK", "DIVERGENTE"}
    summary = client.get(
        "/api/v1/financial/summary?start_date=2026-07-01&end_date=2026-07-31",
        headers=headers,
    ).json()
    assert summary["load_count"] == 2
    assert summary["divergent_freights"] == 1


def test_report_import_rejects_unknown_layout(client):
    response = client.post(
        "/api/v1/imports/copagril-report",
        headers=auth_headers(client),
        files={"file": ("invalid.xls", b"<html>outro arquivo</html>", "text/html")},
    )
    assert response.status_code == 422
