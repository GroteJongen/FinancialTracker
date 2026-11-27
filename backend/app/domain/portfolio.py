"""Pure PLN totals and allocation. Unknown values stay unknown."""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, localcontext

from app.domain.valuation import money


@dataclass(frozen=True)
class Holding:
    asset_class: str
    cost: Decimal | None
    value: Decimal | None
    paid_income: Decimal | None = Decimal("0")


def allocation(rows: list[Holding], basis: str):
    amounts = {
        key: sum((getattr(row, basis) for row in rows if row.asset_class == key), Decimal("0"))
        for key in ("BOND", "ETF", "STOCK", "REIT")
    }
    total = sum(amounts.values(), Decimal("0"))
    if total <= 0:
        return []
    raw = {key: amount / total * Decimal("10000") for key, amount in amounts.items()}
    points = {key: int(value.to_integral_value(rounding=ROUND_FLOOR)) for key, value in raw.items()}
    order = sorted(points, key=lambda key: (-(raw[key] - points[key]), key))
    for key in order[: 10000 - sum(points.values())]:
        points[key] += 1
    result, stop = [], 0
    for key, amount in amounts.items():
        if amount == 0:
            continue
        start = stop
        stop += points[key]
        result.append(
            dict(
                asset_class=key,
                amount=money(amount),
                percent=money(Decimal(points[key]) / 100),
                start=money(Decimal(start) / 100),
                end=money(Decimal(stop) / 100),
            )
        )
    return result


def summarize(rows: list[Holding]):
    for row in rows:
        if row.asset_class not in {"BOND", "ETF", "STOCK", "REIT"}:
            raise ValueError("Unknown asset class")
        for value in (row.cost, row.value, row.paid_income):
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value < 0
            ):
                raise ValueError("Amounts must be finite nonnegative Decimal values")
    with localcontext(prec=max(80, 54 + len(str(max(1, len(rows)))))):
        cost_known = all(row.cost is not None for row in rows)
        value_known = all(row.value is not None for row in rows)
        income_known = all(row.paid_income is not None for row in rows)
        cost = sum((row.cost for row in rows), Decimal("0")) if cost_known else None
        value = sum((row.value for row in rows), Decimal("0")) if value_known else None
        income = sum((row.paid_income for row in rows), Decimal("0")) if income_known else None
        gain = (
            value + income - cost
            if cost is not None and value is not None and income is not None
            else None
        )
        percent = gain / cost * 100 if gain is not None and cost else None
        return dict(
            cost=money(cost),
            value=money(value),
            paid_income=money(income),
            gain=money(gain),
            gain_percent=money(percent),
            known_value=money(
                sum((row.value for row in rows if row.value is not None), Decimal("0"))
            ),
            complete=cost_known and value_known and income_known,
            allocation_value=allocation(rows, "value") if value_known else [],
            allocation_cost=allocation(rows, "cost") if cost_known else [],
        )
