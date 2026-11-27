"""Private stock catalogue and native-currency securities transactions."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("instruments", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "instruments_owner_id_fkey", "instruments", "owners", ["owner_id"], ["id"]
    )
    op.drop_constraint("instruments_isin_key", "instruments", type_="unique")
    op.create_unique_constraint("uq_instruments_owner_isin", "instruments", ["owner_id", "isin"])
    op.create_index(
        "uq_instruments_public_isin",
        "instruments",
        ["isin"],
        unique=True,
        postgresql_where=sa.text("owner_id IS NULL"),
    )
    op.create_check_constraint(
        "ck_instruments_stock_owner", "instruments", "kind <> 'STOCK' OR owner_id IS NOT NULL"
    )
    for table, name in [
        ("purchase_details", "ck_purchase_currency"),
        ("price_observations", "ck_prices_currency"),
    ]:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, "currency IN ('EUR', 'PLN', 'USD')")


def downgrade() -> None:
    connection = op.get_bind()
    pending_data = (
        "SELECT EXISTS (SELECT 1 FROM instruments WHERE owner_id IS NOT NULL) "
        "OR EXISTS (SELECT 1 FROM purchase_details WHERE currency <> 'EUR') "
        "OR EXISTS (SELECT 1 FROM price_observations WHERE currency <> 'EUR')"
    )
    if connection.scalar(sa.text(pending_data)):
        raise RuntimeError(
            "Downgrade blocked: explicitly resolve private stocks "
            "and non-EUR data before reverting."
        )
    for table, name in [
        ("purchase_details", "ck_purchase_currency"),
        ("price_observations", "ck_prices_currency"),
    ]:
        op.drop_constraint(name, table, type_="check")
        op.create_check_constraint(name, table, "currency = 'EUR'")
    op.drop_constraint("ck_instruments_stock_owner", "instruments", type_="check")
    op.drop_index("uq_instruments_public_isin", table_name="instruments")
    op.drop_constraint("uq_instruments_owner_isin", "instruments", type_="unique")
    op.create_unique_constraint("instruments_isin_key", "instruments", ["isin"])
    op.drop_constraint("instruments_owner_id_fkey", "instruments", type_="foreignkey")
    op.drop_column("instruments", "owner_id")
