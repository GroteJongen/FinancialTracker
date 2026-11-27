from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, localcontext
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.application.bonds import bond_account, find_purchase, lock_owner
from app.application.market_prices import mapping_info, selected_price
from app.application.portfolio_contracts import BondValuationCreate
from app.application.purchases import PurchaseError
from app.domain.portfolio import Holding, summarize
from app.domain.purchases import business_today
from app.domain.valuation import Lot, calculate, money
from app.infrastructure import nbp
from app.infrastructure.models import (
    Account,
    BondIssue,
    BondPurchase,
    BondValuation,
    FxRate,
    Instrument,
    Listing,
    Operation,
    PriceObservation,
    PurchaseDetails,
    YahooListing,
)

SCOPES = {
    "ALL": None,
    "STANDARD": {"STANDARD"},
    "IKE": {"IKE", "IKE_BONDS"},
    "IKZE": {"IKZE"},
    "RETIREMENT": {"IKE", "IKE_BONDS", "IKZE"},
}


def records(session: Session, owner_id: UUID, scope: str, *, lock=False):
    query = select(Account).where(Account.owner_id == owner_id).order_by(Account.id)
    if SCOPES[scope] is not None:
        query = query.where(Account.kind.in_(SCOPES[scope]))
    if lock:
        lock_owner(session, owner_id)
        query = query.with_for_update()
    accounts = {account.id: account for account in session.scalars(query)}
    ids = list(accounts)
    securities = list(
        session.execute(
            select(Operation, PurchaseDetails, Listing, Instrument)
            .join(PurchaseDetails, PurchaseDetails.operation_id == Operation.id)
            .join(Listing, Listing.id == Operation.listing_id)
            .join(Instrument, Instrument.id == Listing.instrument_id)
            .where(Operation.account_id.in_(ids))
            .order_by(Operation.trade_date, Operation.id)
        )
    )
    bonds = list(
        session.execute(
            select(BondPurchase, BondIssue)
            .join(BondIssue, BondIssue.id == BondPurchase.issue_id)
            .where(BondPurchase.account_id.in_(ids))
            .order_by(BondPurchase.trade_date, BondPurchase.id)
        )
    )
    return accounts, securities, bonds


def fx_keys(securities):
    today = business_today()
    keys = set()
    for operation, _, listing, _ in securities:
        if listing.currency != "PLN":
            keys.add((listing.currency, operation.trade_date))
            keys.add((listing.currency, today))
    return keys


def cached_rates(session: Session, keys):
    if not keys:
        return {}
    return {
        (row.currency, row.requested_on): row
        for row in session.scalars(
            select(FxRate).where(tuple_(FxRate.currency, FxRate.requested_on).in_(keys))
        )
    }


def get_portfolio(session: Session, owner_id: UUID, scope="ALL"):
    today = business_today()
    with session.begin(), localcontext(prec=80):
        accounts, securities, bonds = records(session, owner_id, scope, lock=True)
        rates = cached_rates(session, fx_keys(securities))
        prices = {}
        for row in session.scalars(
            select(PriceObservation)
            .where(
                PriceObservation.account_id.in_(accounts),
                PriceObservation.observed_on <= today,
            )
            .order_by(
                PriceObservation.observed_on.desc(),
                PriceObservation.recorded_at.desc(),
                PriceObservation.id.desc(),
            )
        ):
            prices.setdefault((row.account_id, row.listing_id), row)
        marks = {}
        for row in session.scalars(
            select(BondValuation)
            .join(BondPurchase)
            .where(
                BondPurchase.account_id.in_(accounts),
                BondValuation.purchase_revision == BondPurchase.revision,
                BondValuation.observed_on <= today,
            )
            .order_by(
                BondValuation.observed_on.desc(),
                BondValuation.recorded_at.desc(),
                BondValuation.id.desc(),
            )
        ):
            marks.setdefault(row.purchase_id, row)
        groups = defaultdict(list)
        for row in securities:
            groups[(row[0].account_id, row[0].listing_id)].append(row)
        automatic = {row.listing_id: row for row in session.scalars(
            select(YahooListing).where(YahooListing.listing_id.in_({key[1] for key in groups}))
        )}
        items, holdings = [], []

        def add(
            account_id,
            label,
            asset_class,
            currency,
            native_cost,
            native_value,
            paid,
            cost_pln,
            value_pln,
            reasons,
            observed_on,
            **extra,
        ):
            account = accounts[account_id]
            gain = (
                value_pln + paid - cost_pln
                if value_pln is not None and cost_pln is not None and paid is not None
                else None
            )
            holdings.append(Holding(asset_class, cost_pln, value_pln, paid))
            items.append(
                dict(
                    account_id=str(account_id),
                    account_name=account.name,
                    account_kind="IKE" if account.kind == "IKE_BONDS" else account.kind,
                    label=label,
                    asset_class=asset_class,
                    currency=currency,
                    native_cost=money(native_cost),
                    native_value=money(native_value),
                    paid_income=money(paid),
                    cost_pln=money(cost_pln),
                    value_pln=money(value_pln),
                    gain_pln=money(gain),
                    reasons=reasons,
                    observed_on=observed_on.isoformat() if observed_on else None,
                    **extra,
                )
            )

        for (account_id, listing_id), lots in groups.items():
            _, _, listing, instrument = lots[0]
            latest_trade = max(row[0].trade_date for row in lots)
            provider = automatic.get(listing_id)
            price = selected_price(prices.get((account_id, listing_id)), provider, listing)
            valid = price is not None and price.observed_on >= latest_trade
            position = calculate(
                [Lot(row[1].quantity, row[1].unit_price, row[1].commission) for row in lots],
                price.price if valid else None,
            )
            reasons = [] if valid else ["missing_price" if price is None else "outdated_price"]
            cost_pln = position.cost if listing.currency == "PLN" else None
            value_pln = position.market_value if listing.currency == "PLN" else None
            if listing.currency != "PLN":
                required = {(listing.currency, row[0].trade_date) for row in lots}
                if required.issubset(rates):
                    cost_pln = sum(
                        (
                            (row[1].quantity * row[1].unit_price + row[1].commission)
                            * rates[(listing.currency, row[0].trade_date)].rate
                            for row in lots
                        ),
                        Decimal("0"),
                    )
                current = rates.get((listing.currency, today))
                if current and position.market_value is not None:
                    value_pln = position.market_value * current.rate
                if cost_pln is None or current is None:
                    reasons.append("missing_fx")
            add(
                account_id,
                f"{listing.symbol} · {listing.mic}",
                instrument.kind,
                listing.currency,
                position.cost,
                position.market_value,
                Decimal("0"),
                cost_pln,
                value_pln,
                reasons,
                price.observed_on if price else None,
                listing_id=str(listing_id),
                quantity=format(position.quantity, "f"),
                price_source=price.source if price else None,
                quoted_at=price.quoted_at.isoformat() if price and price.quoted_at else None,
                fetched_at=price.recorded_at.isoformat() if price else None,
                yahoo=mapping_info(provider),
                stale_price=bool(price and (today - price.observed_on).days > 4),
            )
        for purchase, issue in bonds:
            mark = marks.get(purchase.id)
            cost = purchase.quantity * purchase.unit_price
            value = mark.value if mark else None
            paid = mark.paid_interest if mark else None
            add(
                purchase.account_id,
                issue.series,
                "BOND",
                "PLN",
                cost,
                value,
                paid,
                cost,
                value,
                [] if mark else ["missing_bond_valuation"],
                mark.observed_on if mark else None,
                purchase_id=str(purchase.id),
                purchase_revision=purchase.revision,
                quantity=str(purchase.quantity),
                mark_id=str(mark.id) if mark else None,
                trade_date=purchase.trade_date.isoformat(),
            )
        missing = sorted(fx_keys(securities) - rates.keys())
        return dict(
            scope=scope,
            currency="PLN",
            as_of=today.isoformat(),
            account_count=len(accounts),
            position_count=len(items),
            totals=summarize(holdings),
            positions=items,
            estimated_fx=any(row[2].currency != "PLN" for row in securities),
            by_class=[
                dict(
                    asset_class=key,
                    **summarize([row for row in holdings if row.asset_class == key]),
                )
                for key in ("BOND", "ETF", "STOCK")
            ],
            missing_fx=[
                dict(currency=currency, requested_on=day.isoformat()) for currency, day in missing
            ],
            fx_rates=[
                dict(
                    currency=row.currency,
                    requested_on=row.requested_on.isoformat(),
                    effective_on=row.effective_on.isoformat(),
                    rate=format(row.rate, "f"),
                    table_number=row.table_number,
                    fetched_at=row.fetched_at.isoformat(),
                )
                for _, row in sorted(rates.items())
            ],
        )


def save_bond_valuation(
    session: Session, owner_id: UUID, account_id: UUID, purchase_id: UUID, data: BondValuationCreate
):
    with session.begin():
        lock_owner(session, owner_id)
        bond_account(session, account_id, owner_id, lock=True)
        purchase, _ = find_purchase(session, account_id, purchase_id)
        previous = session.scalar(
            select(BondValuation).where(
                BondValuation.purchase_id == purchase_id,
                BondValuation.request_id == data.request_id,
            )
        )
        if previous is not None:
            if (
                previous.purchase_revision,
                previous.value,
                previous.paid_interest,
                previous.observed_on,
            ) != (data.purchase_revision, data.value, data.paid_interest, data.observed_on):
                raise PurchaseError("Identyfikator zapisu ma już inne dane.", 409)
            return dict(id=str(previous.id)), False
        if purchase.revision != data.purchase_revision:
            raise PurchaseError("Zakup został zmieniony. Odśwież podsumowanie.", 409)
        if data.observed_on < purchase.trade_date:
            raise PurchaseError("Wycena nie może poprzedzać zakupu.", 422)
        mark = BondValuation(purchase_id=purchase_id, **data.model_dump())
        session.add(mark)
        session.flush()
        return dict(id=str(mark.id)), True


def refresh_fx(session: Session, owner_id: UUID, scope="ALL"):
    today = business_today()
    with session.begin():
        _, securities, _ = records(session, owner_id, scope)
        keys = fx_keys(securities)
        cached = cached_rates(session, keys)
    selected = sorted(
        (key for key in keys if key not in cached or key[1] == today),
        key=lambda key: (key[1] != today, key),
    )[:8]

    def fetch(key):
        try:
            return nbp.lookup(*key)
        except nbp.FxUnavailable:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        quotes = list(pool.map(fetch, selected))
    with session.begin():
        for quote in quotes:
            if quote is None:
                continue
            statement = insert(FxRate).values(
                currency=quote.currency,
                requested_on=quote.requested_on,
                effective_on=quote.effective_on,
                rate=quote.rate,
                table_number=quote.table_number,
            )
            statement = statement.on_conflict_do_update(
                index_elements=["currency", "requested_on"],
                set_={
                    "effective_on": statement.excluded.effective_on,
                    "rate": statement.excluded.rate,
                    "table_number": statement.excluded.table_number,
                    "fetched_at": func.clock_timestamp(),
                },
            )
            session.execute(statement)
        remaining = len(keys - cached_rates(session, keys).keys())
    return dict(
        updated=sum(quote is not None for quote in quotes),
        failed=sum(quote is None for quote in quotes),
        remaining=remaining,
    )
