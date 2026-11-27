from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
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


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("owner_id", "isin", name="uq_instruments_owner_isin"),
        Index(
            "uq_instruments_public_isin",
            "isin",
            unique=True,
            postgresql_where=text("owner_id IS NULL"),
        ),
        CheckConstraint(
            "kind <> 'STOCK' OR owner_id IS NOT NULL", name="ck_instruments_stock_owner"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("owners.id"))
    isin: Mapped[str | None] = mapped_column(String(12))
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    distribution: Mapped[str | None] = mapped_column(String(20))


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("instrument_id", "mic", "currency", name="uq_listings_market"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"))
    symbol: Mapped[str] = mapped_column(String(30))
    mic: Mapped[str] = mapped_column(String(4))
    currency: Mapped[str] = mapped_column(String(3))


class Operation(Base):
    __tablename__ = "operations"
    __table_args__ = (
        UniqueConstraint("account_id", "request_id", name="uq_operations_request"),
        CheckConstraint("kind = 'PURCHASE'", name="ck_operations_kind"),
        CheckConstraint("revision > 0", name="ck_operations_revision"),
        Index("ix_operations_account_date", "account_id", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    kind: Mapped[str] = mapped_column(String(20))
    trade_date: Mapped[date] = mapped_column(Date)
    revision: Mapped[int] = mapped_column(server_default=text("1"))
    request_id: Mapped[UUID]
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PurchaseDetails(Base):
    __tablename__ = "purchase_details"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchase_quantity"),
        CheckConstraint("unit_price > 0", name="ck_purchase_price"),
        CheckConstraint("commission >= 0", name="ck_purchase_commission"),
        CheckConstraint("currency IN ('EUR', 'PLN', 'USD')", name="ck_purchase_currency"),
    )

    operation_id: Mapped[UUID] = mapped_column(ForeignKey("operations.id"), primary_key=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    commission: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    currency: Mapped[str] = mapped_column(String(3))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("operation_id", "revision", name="uq_audit_operation_revision"),
        CheckConstraint("kind IN ('CREATE', 'CORRECT')", name="ck_audit_kind"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    operation_id: Mapped[UUID] = mapped_column(ForeignKey("operations.id"))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id"))
    revision: Mapped[int]
    kind: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(String(500))
    before: Mapped[dict[str, str] | None] = mapped_column(JSONB(none_as_null=True))
    after: Mapped[dict[str, str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PriceObservation(Base):
    __tablename__ = "price_observations"
    __table_args__ = (
        UniqueConstraint("account_id", "request_id", name="uq_prices_request"),
        CheckConstraint("price > 0", name="ck_prices_positive"),
        CheckConstraint("currency IN ('EUR', 'PLN', 'USD')", name="ck_prices_currency"),
        CheckConstraint("source = 'MANUAL'", name="ck_prices_source"),
        Index("ix_prices_account_listing_date", "account_id", "listing_id", "observed_on"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("listings.id"))
    request_id: Mapped[UUID]
    price: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    currency: Mapped[str] = mapped_column(String(3))
    observed_on: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )


class BondIssue(Base):
    """Immutable, owner-private snapshot of manually supplied issue parameters."""

    __tablename__ = "bond_issues"
    __table_args__ = (
        UniqueConstraint("owner_id", "series", "terms_version", name="uq_bond_issue_version"),
        CheckConstraint("bond_type IN ('TOS', 'COI', 'EDO')", name="ck_bond_issue_type"),
        CheckConstraint("annual_rate BETWEEN 0 AND 100", name="ck_bond_issue_rate"),
        CheckConstraint("margin BETWEEN 0 AND 100", name="ck_bond_issue_margin"),
        CheckConstraint("bond_type <> 'TOS' OR margin IS NULL", name="ck_bond_issue_tos_margin"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id"))
    series: Mapped[str] = mapped_column(String(7))
    bond_type: Mapped[str] = mapped_column(String(3))
    terms_version: Mapped[str] = mapped_column(String(64))
    annual_rate: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))
    margin: Mapped[Decimal | None] = mapped_column(Numeric(11, 8))
    source_url: Mapped[str | None] = mapped_column(String(2000))


class BondPurchase(Base):
    __tablename__ = "bond_purchases"
    __table_args__ = (
        UniqueConstraint("account_id", "request_id", name="uq_bond_purchase_request"),
        CheckConstraint("quantity BETWEEN 1 AND 999999999", name="ck_bond_purchase_quantity"),
        CheckConstraint("unit_price > 0", name="ck_bond_purchase_price"),
        CheckConstraint("revision > 0", name="ck_bond_purchase_revision"),
        Index("ix_bond_purchases_account_date", "account_id", "trade_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"))
    issue_id: Mapped[UUID] = mapped_column(ForeignKey("bond_issues.id"))
    trade_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    revision: Mapped[int] = mapped_column(server_default=text("1"))
    request_id: Mapped[UUID]
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BondAuditEvent(Base):
    __tablename__ = "bond_audit_events"
    __table_args__ = (
        UniqueConstraint("purchase_id", "revision", name="uq_bond_audit_revision"),
        CheckConstraint("kind IN ('CREATE', 'CORRECT')", name="ck_bond_audit_kind"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    purchase_id: Mapped[UUID] = mapped_column(ForeignKey("bond_purchases.id"))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("owners.id"))
    revision: Mapped[int]
    kind: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(String(500))
    before: Mapped[dict[str, str] | None] = mapped_column(JSONB(none_as_null=True))
    after: Mapped[dict[str, str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
