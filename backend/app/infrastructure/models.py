from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_accounts_owner_name"),
        CheckConstraint(
            "kind IN ('IKE', 'IKZE', 'STANDARD', 'IKE_BONDS')", name="ck_accounts_kind"
        ),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_accounts_currency"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
