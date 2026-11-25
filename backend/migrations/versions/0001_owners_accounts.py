"""Owners and accounts; no assets or transactions yet."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "owners",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("owner_id", "name", name="uq_accounts_owner_name"),
        sa.CheckConstraint(
            "kind IN ('IKE', 'IKZE', 'STANDARD', 'IKE_BONDS')", name="ck_accounts_kind"
        ),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_accounts_currency"),
    )
    op.create_index("ix_accounts_owner_id", "accounts", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_accounts_owner_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("owners")
