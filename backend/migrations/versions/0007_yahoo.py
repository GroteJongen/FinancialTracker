"""Validated Yahoo mapping and last successful quote; manual history is unchanged."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "yahoo_listings",
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id"), primary_key=True),
        sa.Column("id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("symbol", sa.String(30), nullable=False),
        sa.Column("price", sa.Numeric(18, 8)),
        sa.Column("quoted_at", sa.DateTime(timezone=True)),
        sa.Column("fetched_at", sa.DateTime(timezone=True)),
        sa.Column("attempted_at", sa.DateTime(timezone=True)),
        sa.Column("lease", sa.Uuid()),
        sa.Column("failed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("price > 0", name="ck_yahoo_price"),
        sa.CheckConstraint(
            "(price IS NULL AND quoted_at IS NULL AND fetched_at IS NULL) OR "
            "(price IS NOT NULL AND quoted_at IS NOT NULL AND fetched_at IS NOT NULL)",
            name="ck_yahoo_quote_complete",
        ),
    )
    op.execute(table.insert().values(
        listing_id="00000000-0000-4000-8000-000000000004",
        id="00000000-0000-4000-8000-000000000007", symbol="IUSQ.DE",
    ))


def downgrade():
    if op.get_bind().scalar(sa.text(
        "SELECT EXISTS (SELECT 1 FROM yahoo_listings "
        "WHERE listing_id <> '00000000-0000-4000-8000-000000000004')"
    )):
        raise RuntimeError("Export and resolve private Yahoo mappings before reverting.")
    op.drop_table("yahoo_listings")
