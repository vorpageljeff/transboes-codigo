from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LoadVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "load_versions"
    __table_args__ = (UniqueConstraint("load_id", "version"),)

    load_id: Mapped[UUID] = mapped_column(ForeignKey("loads.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(40))
    snapshot: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
