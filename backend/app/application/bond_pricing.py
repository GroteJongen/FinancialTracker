"""Owned portfolio requirements; bounded provider I/O outside transactions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.domain.bond_interest import accrue, anniversary, inflation_month
from app.domain.bonds import BOND_TERMS
from app.domain.purchases import business_today
from app.infrastructure import bond_sources
from app.infrastructure.models import BondSeriesCache, BondValuation, InflationRate


def requirements(session, bonds, today):
    cached = {row.series: row for row in session.scalars(select(BondSeriesCache))}
    rates = {(row.year, row.month) for row in session.scalars(select(InflationRate))}
    marked = set(
        session.scalars(
            select(BondValuation.purchase_id).where(
                BondValuation.purchase_id.in_([purchase.id for purchase, _ in bonds]),
                BondValuation.observed_on <= today,
            )
        )
    )
    # A manual mark only applies to its current purchase revision.
    valid_marks = {
        (row.purchase_id, row.purchase_revision)
        for row in session.scalars(
            select(BondValuation).where(
                BondValuation.purchase_id.in_(marked), BondValuation.observed_on <= today
            )
        )
    }
    series, months = set(), set()
    for purchase, issue in bonds:
        if (purchase.id, purchase.revision) in valid_marks:
            continue
        known = cached.get(issue.series)
        if (
            issue.annual_rate is None or (issue.bond_type != "TOS" and issue.margin is None)
        ) and known is None:
            series.add(issue.series)
        if issue.bond_type != "TOS":
            end = min(today, anniversary(purchase.trade_date, BOND_TERMS[issue.bond_type]))
            for period in range(1, BOND_TERMS[issue.bond_type]):
                start = anniversary(purchase.trade_date, period)
                if start >= end:
                    break
                key = inflation_month(start)
                if key not in rates:
                    months.add(key)
    return series, months


def requirement_keys(session, bonds, today):
    series, months = requirements(session, bonds, today)
    return sorted(
        ["SERIES:" + key for key in series] + [f"CPI:{year}-{month:02d}" for year, month in months]
    )


def cached_inputs(session):
    return (
        {row.series: row for row in session.scalars(select(BondSeriesCache))},
        {(row.year, row.month): row.rate for row in session.scalars(select(InflationRate))},
    )


def calculate_bond(purchase, issue, today, terms, inflation):
    known = terms.get(issue.series)
    rate = (
        issue.annual_rate if issue.annual_rate is not None else known.annual_rate if known else None
    )
    margin = issue.margin if issue.margin is not None else known.margin if known else None
    mode = "PAYOUT" if issue.bond_type == "COI" else "CAPITALIZE"
    result = accrue(
        issue.bond_type,
        purchase.trade_date,
        purchase.quantity,
        rate,
        margin,
        mode,
        today,
        inflation,
    )
    return result, mode, known.source_url if known else issue.source_url


def refresh_bond_data(session, owner_id, scope="ALL", portfolio_id=None):
    from app.application.portfolio import records

    today = business_today()
    with session.begin():
        _, _, bonds = records(session, owner_id, scope, portfolio_id=portfolio_id)
        series, months = requirements(session, bonds, today)
    selected = sorted(series)[:4]

    def fetch_terms(key):
        try:
            return bond_sources.terms(key)
        except bond_sources.SourceUnavailable:
            return None

    cpi, cpi_failed = {}, False
    with ThreadPoolExecutor(max_workers=5) as pool:
        cpi_task = pool.submit(bond_sources.inflation) if months else None
        fetched = list(pool.map(fetch_terms, selected))
        if cpi_task is not None:
            try:
                cpi = cpi_task.result()
            except bond_sources.SourceUnavailable:
                cpi_failed = True
    updated = 0
    with session.begin():
        for item in fetched:
            if item is not None:
                result = session.execute(
                    insert(BondSeriesCache)
                    .values(
                        series=item.series,
                        annual_rate=item.annual_rate,
                        margin=item.margin,
                        source_url=item.source_url,
                    )
                    .on_conflict_do_nothing()
                )
                updated += result.rowcount
        for (year, month), rate in cpi.items():
            if date(year, month, 1) >= today.replace(day=1):
                continue
            result = session.execute(
                insert(InflationRate)
                .values(year=year, month=month, rate=rate, source_url=bond_sources.GUS_URL)
                .on_conflict_do_nothing()
            )
            updated += result.rowcount
        # Re-read ownership and composition: no HTTP result can modify holdings.
        _, _, bonds = records(session, owner_id, scope, portfolio_id=portfolio_id)
        remaining = len(requirement_keys(session, bonds, today))
    return dict(
        updated=updated,
        failed=sum(item is None for item in fetched) + int(cpi_failed),
        remaining=remaining,
    )
