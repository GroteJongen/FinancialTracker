"""User-defined portfolios and listed REIT ownership."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portfolio_groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.UniqueConstraint("owner_id", "name", name="uq_portfolio_group_name"),
    )
    op.create_index("ix_portfolio_groups_owner_id", "portfolio_groups", ["owner_id"])
    op.create_table(
        "portfolio_accounts",
        sa.Column(
            "portfolio_id", sa.Uuid(), sa.ForeignKey("portfolio_groups.id"), primary_key=True
        ),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), primary_key=True),
    )
    op.drop_constraint("ck_instruments_stock_owner", "instruments")
    op.create_check_constraint(
        "ck_instruments_stock_owner",
        "instruments",
        "kind NOT IN ('STOCK', 'REIT') OR owner_id IS NOT NULL",
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM instruments WHERE kind = 'REIT' OR (kind = 'ETF' AND owner_id IS NOT NULL))")):
        raise RuntimeError("Resolve private ETF/REIT holdings before reverting their support.")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM portfolio_groups)")):
        raise RuntimeError("Export and resolve saved portfolios before reverting.")
    op.drop_table("portfolio_accounts")
    op.drop_table("portfolio_groups")
    op.drop_constraint("ck_instruments_stock_owner", "instruments")
    op.create_check_constraint(
        "ck_instruments_stock_owner", "instruments", "kind <> 'STOCK' OR owner_id IS NOT NULL"
    )
