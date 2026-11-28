"""Public issue terms and historical GUS year-on-year CPI cache."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bond_series_cache",
        sa.CheckConstraint("annual_rate BETWEEN 0 AND 100 AND (margin IS NULL OR margin BETWEEN 0 AND 100)", name="ck_bond_series_cache_rates"),
        sa.Column("series", sa.String(7), primary_key=True),
        sa.Column("annual_rate", sa.Numeric(11, 8), nullable=False),
        sa.Column("margin", sa.Numeric(11, 8)),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.clock_timestamp()),
    )
    op.create_table(
        "inflation_rates",
        sa.CheckConstraint("year BETWEEN 2000 AND 2099 AND month BETWEEN 1 AND 12 AND rate > -100 AND rate < 900", name="ck_inflation_rates_values"),
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("month", sa.Integer(), primary_key=True),
        sa.Column("rate", sa.Numeric(11, 8), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.clock_timestamp()),
    )


def downgrade():
    op.drop_table("inflation_rates")
    op.drop_table("bond_series_cache")
