import enum
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ImportRunStatus(str, enum.Enum):
    PROCESSING = "PROCESSANDO"
    COMPLETED = "CONCLUIDA"
    COMPLETED_WITH_ERRORS = "CONCLUIDA_COM_ERROS"
    FAILED = "FALHOU"
    DUPLICATE = "DUPLICADA"


class ImportProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "import_profiles"
    name: Mapped[str] = mapped_column(String(120), unique=True)
    source_type: Mapped[str] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ImportProfileVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "import_profile_versions"
    __table_args__ = (UniqueConstraint("profile_id", "version"),)
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("import_profiles.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    field_mapping: Mapped[str] = mapped_column(Text)
    validation_rules: Mapped[str] = mapped_column(Text, default="{}")
    cancellation_rules: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ImportRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "import_runs"
    profile_version_id: Mapped[UUID] = mapped_column(ForeignKey("import_profile_versions.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    source_checksum: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[ImportRunStatus] = mapped_column(
        Enum(ImportRunStatus, values_callable=lambda enum: [item.value for item in enum])
    )
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="{}")


class ImportRow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "import_rows"
    __table_args__ = (UniqueConstraint("import_run_id", "row_number"),)
    import_run_id: Mapped[UUID] = mapped_column(ForeignKey("import_runs.id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    external_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(40))
    raw_data: Mapped[str] = mapped_column(Text)
    errors: Mapped[str] = mapped_column(Text, default="[]")
    style_markers: Mapped[str] = mapped_column(Text, default="[]")
