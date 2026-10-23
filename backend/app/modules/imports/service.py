import hashlib
import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financial import RevenueEntry
from app.models.freight import FreightValidation, FreightValidationStatus
from app.models.imports import (
    ImportProfile,
    ImportProfileVersion,
    ImportRow,
    ImportRun,
    ImportRunStatus,
)
from app.models.load import Load, LoadStatus
from app.models.user import User
from app.modules.audit.service import record_audit
from app.modules.imports.parser import REPORT_MAPPING, ParsedReportRow, parse_copagril_report


class DuplicateImportError(Exception):
    def __init__(self, run: ImportRun):
        self.run = run


def get_or_create_profile(db: Session) -> ImportProfileVersion:
    profile = db.scalar(
        select(ImportProfile).where(ImportProfile.name == "Copagril Viagens HTML v1")
    )
    if profile is None:
        profile = ImportProfile(name="Copagril Viagens HTML v1", source_type="HTML_XLS")
        db.add(profile)
        db.flush()
        version = ImportProfileVersion(
            profile_id=profile.id,
            version=1,
            field_mapping=json.dumps(REPORT_MAPPING),
            validation_rules=json.dumps(
                {"required_for_import": ["external_id", "received_at", "received_freight"]}
            ),
            cancellation_rules=json.dumps(
                {
                    "detectors": [],
                    "note": "Amarelo neste relatório significa divergência, não cancelamento.",
                }
            ),
        )
        db.add(version)
        db.flush()
        return version
    return db.scalar(
        select(ImportProfileVersion)
        .where(
            ImportProfileVersion.profile_id == profile.id, ImportProfileVersion.is_active.is_(True)
        )
        .order_by(ImportProfileVersion.version.desc())
    )


def import_copagril_report(db: Session, *, content: bytes, filename: str, user: User) -> ImportRun:
    checksum = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(ImportRun).where(ImportRun.source_checksum == checksum))
    if existing:
        raise DuplicateImportError(existing)
    version = get_or_create_profile(db)
    run = ImportRun(
        profile_version_id=version.id,
        user_id=user.id,
        filename=filename[:255],
        source_checksum=checksum,
        status=ImportRunStatus.PROCESSING,
    )
    db.add(run)
    db.flush()
    rows = parse_copagril_report(content)
    run.total_rows = len(rows)
    differences = 0
    for row in rows:
        _import_row(db, run, row)
        stored = db.scalar(select(Load).where(Load.external_id == row.values["external_id"]))
        if stored and stored.reference == f"COP-{row.values['external_id']}":
            if (
                db.scalar(
                    select(ImportRow).where(
                        ImportRow.import_run_id == run.id, ImportRow.row_number == row.row_number
                    )
                ).status
                == "DUPLICADA"
            ):
                run.duplicate_rows += 1
            else:
                run.imported_rows += 1
                received = row.decimal("received_freight")
                expected = row.decimal("calculated_freight")
                if received is not None and expected is not None and received != expected:
                    differences += 1
    run.status = (
        ImportRunStatus.COMPLETED_WITH_ERRORS if run.error_rows else ImportRunStatus.COMPLETED
    )
    run.summary = json.dumps(
        {"freight_differences": differences, "yellow_rows": sum(r.yellow_marked for r in rows)}
    )
    record_audit(
        db,
        user_id=user.id,
        action="COPAGRIL_REPORT_IMPORTED",
        entity_type="import_run",
        entity_id=str(run.id),
        details={
            "rows": run.total_rows,
            "imported": run.imported_rows,
            "duplicates": run.duplicate_rows,
        },
    )
    db.commit()
    db.refresh(run)
    return run


def _import_row(db: Session, run: ImportRun, row: ParsedReportRow) -> None:
    raw = json.dumps(row.values, ensure_ascii=False)
    external_id = row.values["external_id"]
    existing_load = db.scalar(select(Load).where(Load.external_id == external_id))
    if existing_load:
        if (existing_load.freight_value != row.decimal("received_freight") or existing_load.expected_freight_value != row.decimal("calculated_freight") or existing_load.weight_kg != row.decimal("live_weight") or existing_load.origin != row.values["producer"]):
            raise ValueError(f"Viagem {external_id}: dados diferentes do registro existente; revisão necessária")
        db.add(
            ImportRow(
                import_run_id=run.id,
                row_number=row.row_number,
                external_id=external_id,
                status="DUPLICADA",
                raw_data=raw,
                style_markers=json.dumps(["YELLOW"] if row.yellow_marked else []),
            )
        )
        db.flush()
        return
    try:
        received = row.decimal("received_freight")
        expected = row.decimal("calculated_freight")
        if received is None:
            raise ValueError("received_freight: valor obrigatório")
        load = Load(
            reference=f"COP-{external_id}",
            external_id=external_id,
            customer="Copagril",
            product="Suínos",
            origin=row.values["producer"],
            destination=row.values["facility"],
            facility_code=row.values["facility"].split(":", 1)[-1].split("-", 1)[0],
            weight_kg=row.decimal("live_weight") or Decimal(0),
            quantity=row.integer("quantity"),
            distance_km=row.decimal("distance_km"),
            freight_value=received,
            expected_freight_value=expected,
            received_at=row.received_datetime(),
            pickup_date=row.received_datetime().date(),
            delivery_date=row.received_datetime().date(),
            status=LoadStatus.DELIVERED,
            source="COPAGRIL_REPORT",
            notes=f"GTA {row.values['gta']} · Romaneio {row.values['manifest']} · Lote {row.values['lot']}",
        )
        db.add(load)
        db.flush()
        db.add(
            RevenueEntry(
                load_id=load.id,
                amount=received,
                recognized_on=load.delivery_date,
                source="COPAGRIL_REPORT",
            )
        )
        difference = received - expected if expected is not None else None
        db.add(
            FreightValidation(
                load_id=load.id,
                mode="REPORT_COMPARE",
                received_amount=received,
                expected_amount=expected,
                difference=difference,
                status=(
                    FreightValidationStatus.WAITING_RULE
                    if expected is None
                    else FreightValidationStatus.OK
                    if difference == 0
                    else FreightValidationStatus.DIVERGENT
                ),
                explanation="Comparação entre as colunas de frete recebido e calculado do relatório.",
            )
        )
        db.add(
            ImportRow(
                import_run_id=run.id,
                row_number=row.row_number,
                external_id=external_id,
                status="IMPORTADA",
                raw_data=raw,
                style_markers=json.dumps(["YELLOW"] if row.yellow_marked else []),
            )
        )
        db.flush()
    except (ValueError, TypeError) as exc:
        run.error_rows += 1
        db.add(
            ImportRow(
                import_run_id=run.id,
                row_number=row.row_number,
                external_id=external_id,
                status="ERRO",
                raw_data=raw,
                errors=json.dumps([str(exc)], ensure_ascii=False),
                style_markers=json.dumps(["YELLOW"] if row.yellow_marked else []),
            )
        )
