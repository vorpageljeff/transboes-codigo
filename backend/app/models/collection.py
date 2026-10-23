from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CollectionCase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "collection_cases"
    load_id: Mapped[UUID] = mapped_column(ForeignKey("loads.id"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="EM_REVISAO")
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    received_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    reason: Mapped[str] = mapped_column(Text)
    evidence_reference: Mapped[str] = mapped_column(String(500))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    receipt_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
