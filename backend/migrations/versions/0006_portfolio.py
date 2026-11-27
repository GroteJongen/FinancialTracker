"""Append-only bond valuations and public reference FX cache."""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bond_valuations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("purchase_id", sa.Uuid(), sa.ForeignKey("bond_purchases.id"), nullable=False),
        sa.Column("purchase_revision", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Numeric(22, 2), nullable=False),
        sa.Column("paid_interest", sa.Numeric(22, 2), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.clock_timestamp()),
        sa.UniqueConstraint("purchase_id", "request_id", name="uq_bond_valuations_request"),
        sa.CheckConstraint("value >= 0 AND paid_interest >= 0", name="ck_bond_valuations_amounts"),
        sa.CheckConstraint("purchase_revision > 0", name="ck_bond_valuations_revision"),
    )
    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("requested_on", sa.Date(), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("table_number", sa.String(40), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.clock_timestamp()),
        sa.UniqueConstraint("currency", "requested_on", name="uq_fx_rates_requested"),
        sa.CheckConstraint("currency IN ('EUR', 'USD')", name="ck_fx_rates_currency"),
        sa.CheckConstraint("rate > 0 AND effective_on <= requested_on", name="ck_fx_rates_values"),
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM bond_valuations)")):
        raise RuntimeError("Export and explicitly resolve bond valuations before reverting.")
    op.drop_table("fx_rates")
    op.drop_table("bond_valuations")
