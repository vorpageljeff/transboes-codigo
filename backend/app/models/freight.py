import enum
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FreightValidationStatus(str, enum.Enum):
    PENDING = "PENDENTE"
    OK = "CONFERIDO_OK"
    DIVERGENT = "DIVERGENTE"
    MANUALLY_ADJUSTED = "AJUSTADO_MANUALMENTE"
    WAITING_RULE = "AGUARDANDO_REGRA"
    NOT_APPLICABLE = "NAO_APLICAVEL"


class FreightRuleSet(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freight_rule_sets"
    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FreightRuleVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freight_rule_versions"
    rule_set_id: Mapped[UUID] = mapped_column(ForeignKey("freight_rule_sets.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    configuration: Mapped[str] = mapped_column(Text, default="{}")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class FreightValidation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freight_validations"
    load_id: Mapped[UUID] = mapped_column(ForeignKey("loads.id"), index=True)
    rule_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("freight_rule_versions.id"), nullable=True
    )
    mode: Mapped[str] = mapped_column(String(30))
    received_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    difference: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[FreightValidationStatus] = mapped_column(
        Enum(FreightValidationStatus, values_callable=lambda enum: [item.value for item in enum])
    )
    explanation: Mapped[str] = mapped_column(Text)


class FreightManualAdjustment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freight_manual_adjustments"
    validation_id: Mapped[UUID] = mapped_column(ForeignKey("freight_validations.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    previous_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    adjusted_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text)


class FreightCalculation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "freight_calculations"

    load_id: Mapped[UUID] = mapped_column(ForeignKey("loads.id"), index=True)
    rule_version_id: Mapped[UUID] = mapped_column(ForeignKey("freight_rule_versions.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    input_snapshot: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    explanation: Mapped[str] = mapped_column(Text)
