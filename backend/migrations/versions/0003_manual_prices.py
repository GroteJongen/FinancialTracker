"""Private, append-only manual prices for an account and listing."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "price_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("price", sa.Numeric(18, 8), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.clock_timestamp(),
        ),
        sa.UniqueConstraint("account_id", "request_id", name="uq_prices_request"),
        sa.CheckConstraint("price > 0", name="ck_prices_positive"),
        sa.CheckConstraint("currency = 'EUR'", name="ck_prices_currency"),
        sa.CheckConstraint("source = 'MANUAL'", name="ck_prices_source"),
    )
    op.create_index(
        "ix_prices_account_listing_date",
        "price_observations",
        ["account_id", "listing_id", "observed_on"],
    )


def downgrade() -> None:
    op.drop_index("ix_prices_account_listing_date", table_name="price_observations")
    op.drop_table("price_observations")
