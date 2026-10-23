import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    details: dict | None = None,
    decision_source: str = "USER",
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details or {}, ensure_ascii=False, default=str),
            decision_source=decision_source,
        )
    )
