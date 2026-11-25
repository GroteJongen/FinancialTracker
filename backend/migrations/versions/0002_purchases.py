"""Instrument catalogue, purchase operations and append-only application audit."""

from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

INSTRUMENT_ID = UUID("00000000-0000-4000-8000-000000000003")
LISTING_ID = UUID("00000000-0000-4000-8000-000000000004")


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("isin", sa.String(12), nullable=True, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("distribution", sa.String(20), nullable=True),
    )
    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("instrument_id", sa.Uuid(), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("symbol", sa.String(30), nullable=False),
        sa.Column("mic", sa.String(4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.UniqueConstraint("instrument_id", "mic", "currency", name="uq_listings_market"),
    )
    op.create_table(
        "operations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("account_id", "request_id", name="uq_operations_request"),
        sa.CheckConstraint("kind = 'PURCHASE'", name="ck_operations_kind"),
        sa.CheckConstraint("revision > 0", name="ck_operations_revision"),
    )
    op.create_index("ix_operations_account_date", "operations", ["account_id", "trade_date"])
    op.create_table(
        "purchase_details",
        sa.Column("operation_id", sa.Uuid(), sa.ForeignKey("operations.id"), primary_key=True),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("commission", sa.Numeric(18, 8), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_quantity"),
        sa.CheckConstraint("unit_price > 0", name="ck_purchase_price"),
        sa.CheckConstraint("commission >= 0", name="ck_purchase_commission"),
        sa.CheckConstraint("currency = 'EUR'", name="ck_purchase_currency"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("operation_id", sa.Uuid(), sa.ForeignKey("operations.id"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("operation_id", "revision", name="uq_audit_operation_revision"),
        sa.CheckConstraint("kind IN ('CREATE', 'CORRECT')", name="ck_audit_kind"),
    )
    op.execute(
        sa.text(
            "INSERT INTO instruments (id, isin, name, kind, distribution) VALUES "
            "(:id, 'IE00B6R52259', 'iShares MSCI ACWI UCITS ETF USD (Acc)', 'ETF', 'ACC')"
        ).bindparams(id=INSTRUMENT_ID)
    )
    op.execute(
        sa.text(
            "INSERT INTO listings (id, instrument_id, symbol, mic, currency) "
            "VALUES (:id, :instrument_id, 'IUSQ', 'XETR', 'EUR')"
        ).bindparams(id=LISTING_ID, instrument_id=INSTRUMENT_ID)
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("purchase_details")
    op.drop_index("ix_operations_account_date", table_name="operations")
    op.drop_table("operations")
    op.drop_table("listings")
    op.drop_table("instruments")
