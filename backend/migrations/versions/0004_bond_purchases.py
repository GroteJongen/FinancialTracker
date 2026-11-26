"""Private issue snapshots, retail bond purchases and atomic correction audit."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bond_issues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("series", sa.String(7), nullable=False),
        sa.Column("bond_type", sa.String(3), nullable=False),
        sa.Column("terms_version", sa.String(64), nullable=False),
        sa.Column("annual_rate", sa.Numeric(11, 8)),
        sa.Column("margin", sa.Numeric(11, 8)),
        sa.Column("source_url", sa.String(2000)),
        sa.UniqueConstraint("owner_id", "series", "terms_version", name="uq_bond_issue_version"),
        sa.CheckConstraint("bond_type IN ('TOS', 'COI', 'EDO')", name="ck_bond_issue_type"),
        sa.CheckConstraint("annual_rate BETWEEN 0 AND 100", name="ck_bond_issue_rate"),
        sa.CheckConstraint("margin BETWEEN 0 AND 100", name="ck_bond_issue_margin"),
        sa.CheckConstraint("bond_type <> 'TOS' OR margin IS NULL", name="ck_bond_issue_tos_margin"),
    )
    op.create_table(
        "bond_purchases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("issue_id", sa.Uuid(), sa.ForeignKey("bond_issues.id"), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("account_id", "request_id", name="uq_bond_purchase_request"),
        sa.CheckConstraint("quantity BETWEEN 1 AND 999999999", name="ck_bond_purchase_quantity"),
        sa.CheckConstraint("unit_price > 0", name="ck_bond_purchase_price"),
        sa.CheckConstraint("revision > 0", name="ck_bond_purchase_revision"),
    )
    op.create_index("ix_bond_purchases_account_date", "bond_purchases", ["account_id", "trade_date"])
    op.create_table(
        "bond_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("purchase_id", sa.Uuid(), sa.ForeignKey("bond_purchases.id"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("before", postgresql.JSONB(none_as_null=True)),
        sa.Column("after", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("purchase_id", "revision", name="uq_bond_audit_revision"),
        sa.CheckConstraint("kind IN ('CREATE', 'CORRECT')", name="ck_bond_audit_kind"),
    )


def downgrade() -> None:
    op.drop_table("bond_audit_events")
    op.drop_index("ix_bond_purchases_account_date", table_name="bond_purchases")
    op.drop_table("bond_purchases")
    op.drop_table("bond_issues")
