from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.purchases import PurchaseError, matching_currency, owned_account, supported_account, supported_listing
from app.application.valuation_contracts import (
    DisplayPosition,
    PriceCreate,
    PriceResponse,
    ValuationResponse,
)
from app.domain.valuation import Lot, calculate, money
from app.infrastructure.models import Operation, PriceObservation, PurchaseDetails


def latest_trade_date(session: Session, account_id: UUID, listing_id: UUID):
    return session.scalar(
        select(func.max(Operation.trade_date)).where(
            Operation.account_id == account_id,
            Operation.listing_id == listing_id,
            Operation.kind == "PURCHASE",
        )
    )


def create_price(session: Session, owner_id: UUID, account_id: UUID, data: PriceCreate):
    with session.begin():
        account = owned_account(session, account_id, owner_id, lock=True)
        listing = supported_listing(session, data.listing_id, owner_id)
        matching_currency(listing, data.currency)
        supported_account(session, account, listing)
        existing = session.scalar(
            select(PriceObservation).where(
                PriceObservation.account_id == account_id,
                PriceObservation.request_id == data.request_id,
            )
        )
        if existing is not None:
            if (
                existing.listing_id != data.listing_id
                or existing.price != data.price
                or existing.currency != data.currency
                or existing.observed_on != data.observed_on
            ):
                raise PurchaseError("Identyfikator zapisu był już użyty dla innych danych.", 409)
            return PriceResponse.model_validate(existing), False
        last_trade = latest_trade_date(session, account_id, data.listing_id)
        if last_trade and data.observed_on < last_trade:
            raise PurchaseError(
                "Data wyceny nie może być wcześniejsza niż ostatni zakup: "
                + last_trade.strftime("%d.%m.%Y")
                + ".",
                422,
            )
        observation = PriceObservation(
            account_id=account_id,
            listing_id=data.listing_id,
            request_id=data.request_id,
            price=data.price,
            currency=data.currency,
            observed_on=data.observed_on,
            source="MANUAL",
        )
        session.add(observation)
        session.flush()
        session.refresh(observation)
        return PriceResponse.model_validate(observation), True


def get_valuation(session: Session, owner_id: UUID, account_id: UUID, listing_id: UUID):
    # All writes on this ledger lock its account first, so these reads form a coherent view.
    with session.begin():
        account = owned_account(session, account_id, owner_id, lock=True)
        listing = supported_listing(session, listing_id, owner_id)
        supported_account(session, account, listing)
        purchases = list(
            session.execute(
                select(
                    Operation.trade_date,
                    PurchaseDetails.quantity,
                    PurchaseDetails.unit_price,
                    PurchaseDetails.commission,
                )
                .join(PurchaseDetails, PurchaseDetails.operation_id == Operation.id)
                .where(
                    Operation.account_id == account_id,
                    Operation.listing_id == listing_id,
                    Operation.kind == "PURCHASE",
                )
            )
        )
        history = list(
            session.scalars(
                select(PriceObservation)
                .where(
                    PriceObservation.account_id == account_id,
                    PriceObservation.listing_id == listing_id,
                )
                .order_by(
                    PriceObservation.observed_on.desc(),
                    PriceObservation.recorded_at.desc(),
                    PriceObservation.id.desc(),
                )
            )
        )
        latest_trade = max((row.trade_date for row in purchases), default=None)
        price = history[0] if history else None
        outdated = bool(price and latest_trade and price.observed_on < latest_trade)
        position = calculate(
            [Lot(row.quantity, row.unit_price, row.commission) for row in purchases],
            price.price if price and not outdated else None,
        )
        status = (
            "empty"
            if not purchases
            else ("unpriced" if price is None else "outdated" if outdated else "priced")
        )
        return ValuationResponse(
            account_id=account_id,
            listing_id=listing_id,
            symbol=listing.symbol,
            currency=listing.currency,
            status=status,
            latest_trade_date=latest_trade,
            quantity=position.quantity,
            cost=position.cost,
            average_cost=position.average_cost,
            market_value=position.market_value,
            gain=position.gain,
            gain_percent=position.gain_percent,
            price=PriceResponse.model_validate(price) if price else None,
            history=[PriceResponse.model_validate(item) for item in history],
            display=DisplayPosition(
                cost=money(position.cost),
                average_cost=money(position.average_cost),
                market_value=money(position.market_value),
                gain=money(position.gain),
                gain_percent=money(position.gain_percent),
            ),
        )
