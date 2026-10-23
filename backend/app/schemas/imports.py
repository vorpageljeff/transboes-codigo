from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.imports import ImportRunStatus


class ImportRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str
    source_checksum: str
    status: ImportRunStatus
    total_rows: int
    imported_rows: int
    duplicate_rows: int
    error_rows: int
    summary: str
    created_at: datetime
