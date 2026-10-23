from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

REPORT_MAPPING = {
    "facility": 0,
    "carrier": 1,
    "affiliate": 2,
    "producer": 3,
    "city": 4,
    "external_id": 5,
    "vehicle_plate": 6,
    "vehicle_model": 7,
    "driver": 8,
    "received_at": 9,
    "gta": 10,
    "manifest": 11,
    "lot": 12,
    "invoice_description": 13,
    "live_weight": 14,
    "quantity": 15,
    "distance_km": 16,
    "received_freight": 17,
    "calculated_freight": 18,
}


@dataclass(frozen=True)
class ParsedReportRow:
    row_number: int
    values: dict[str, str]
    yellow_marked: bool

    def decimal(self, field: str) -> Decimal | None:
        value = self.values.get(field, "").strip()
        if not value:
            return None
        try:
            result = Decimal(value.replace(".", "").replace(",", "."))
            if not result.is_finite() or result < 0:
                raise ValueError(f"{field}: valor deve ser finito e não negativo")
            return result
        except InvalidOperation as exc:
            raise ValueError(f"{field}: número inválido '{value}'") from exc

    def integer(self, field: str) -> int | None:
        value = self.values.get(field, "").strip()
        return int(value) if value else None

    def received_datetime(self) -> datetime:
        return datetime.strptime(self.values["received_at"], "%d/%m/%y %H:%M").replace(
            tzinfo=ZoneInfo("America/Sao_Paulo")
        )


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[dict[str, str]]] = []
        self._row: list[dict[str, str]] | None = None
        self._cell: dict[str, str | list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = {"class": attributes.get("class") or "", "text": []}

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            text = self._cell["text"]
            assert isinstance(text, list)
            text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cell is not None and self._row is not None:
            text = self._cell["text"]
            assert isinstance(text, list)
            self._row.append(
                {"class": str(self._cell["class"]), "text": " ".join(" ".join(text).split())}
            )
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def parse_copagril_report(content: bytes) -> list[ParsedReportRow]:
    text = content.decode("utf-8-sig")
    if "Relatório das Viagens de Suínos" not in text:
        raise ValueError("O arquivo não é um relatório de viagens de suínos reconhecido")
    parser = _TableParser()
    parser.feed(text)
    if not parser.rows or len(parser.rows[0]) != len(REPORT_MAPPING):
        raise ValueError("Cabeçalho do relatório incompatível com o perfil ativo")
    expected_headers = ["Filial", "Transportador", "Filiada", "Produtor", "Cidade", "Viagem", "Placa Veículo", "Modelo Veíc.", "Motorista", "Data Recebimento", "N° da GTA", "Romaneio", "Lote", "Descrição Nota Fiscal", "Peso Vivo", "Quant.", "Distância", "R$ Frete MS Total", "R$ Frete Romaneiro Calculado"]
    normalize = lambda value: "".join(value.casefold().split())
    if [normalize(c["text"]) for c in parser.rows[0]] != [normalize(h) for h in expected_headers]:
        raise ValueError("Nomes ou ordem das colunas incompatíveis com o perfil")
    if len(parser.rows) > 5001:
        raise ValueError("Limite de 5000 linhas por importação")
    parsed: list[ParsedReportRow] = []
    for row_number, cells in enumerate(parser.rows[1:], start=2):
        if len(cells) != len(REPORT_MAPPING):
            raise ValueError(f"Linha {row_number}: quantidade de colunas inválida")
        values = {field: cells[index]["text"] for field, index in REPORT_MAPPING.items()}
        if not values["external_id"]:
            raise ValueError(f"Linha {row_number}: viagem sem identificador")
        parsed.append(
            ParsedReportRow(
                row_number=row_number,
                values=values,
                yellow_marked=any(cell["class"] in {"c66", "c67"} for cell in cells),
            )
        )
    if not parsed:
        raise ValueError("Nenhuma linha de viagem foi encontrada")
    return parsed
