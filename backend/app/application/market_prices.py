from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.purchases import PurchaseError, supported_listing
from app.application.valuation_contracts import PriceResponse
from app.infrastructure import yahoo
from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.infrastructure.models import Account, Instrument, Listing, Operation, YahooListing

COOLDOWN = timedelta(minutes=5)


class MappingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value):
        return yahoo.symbol_text(value.strip().upper())


def configure(session: Session, owner_id: UUID, listing_id: UUID, symbol: str | None):
    with session.begin():
        listing = supported_listing(session, listing_id, owner_id)
        if listing.mic not in yahoo.MARKETS:
            raise PurchaseError("Yahoo obsluguje obecnie XETR, XNAS, XNYS i XWAR.", 422)
        if listing_id == IUSQ_LISTING_ID and symbol not in (None, "IUSQ.DE"):
            raise PurchaseError("Dla IUSQ na Xetrze uzyj IUSQ.DE.", 422)
        # Lock the parent even when the mapping does not exist yet.
        session.execute(select(Listing).where(Listing.id == listing_id).with_for_update())
        row = session.get(YahooListing, listing_id, with_for_update=True)
        if symbol is None:
            if row:
                session.delete(row)
        elif row is None:
            session.add(YahooListing(listing_id=listing_id, symbol=symbol))
        elif row.symbol != symbol:
            row.symbol = symbol
            row.price = row.quoted_at = row.fetched_at = row.attempted_at = row.lease = None
            row.failed = False
    return dict(symbol=symbol)


def mapping_info(row: YahooListing | None):
    return (
        None
        if row is None
        else dict(
            symbol=row.symbol,
            failed=row.failed,
            attempted_at=row.attempted_at.isoformat() if row.attempted_at else None,
            fetched_at=row.fetched_at.isoformat() if row.fetched_at else None,
            quoted_at=row.quoted_at.isoformat() if row.quoted_at else None,
        )
    )


def selected_price(manual, automatic: YahooListing | None, listing: Listing):
    """Newest market day wins. On the same day compare real quote time to manual save time."""
    chosen = PriceResponse.model_validate(manual) if manual else None
    if automatic is None or automatic.price is None:
        return chosen
    day = yahoo.market_day(automatic.quoted_at, listing.mic)
    if chosen and (chosen.observed_on, chosen.recorded_at) >= (day, automatic.quoted_at):
        return chosen
    return PriceResponse(
        id=automatic.id,
        listing_id=listing.id,
        price=automatic.price,
        currency=listing.currency,
        observed_on=day,
        source="YAHOO",
        recorded_at=automatic.fetched_at,
        quoted_at=automatic.quoted_at,
        provider_symbol=automatic.symbol,
    )


def refresh(session: Session, owner_id: UUID):
    # Select only owned holdings, not the user's entire catalogue or another owner's symbols.
    with session.begin():
        held = select(Operation.listing_id).join(Account).where(Account.owner_id == owner_id)
        rows = list(
            session.execute(
                select(YahooListing, Listing, Instrument)
                .join(Listing, Listing.id == YahooListing.listing_id)
                .join(Instrument, Instrument.id == Listing.instrument_id)
                .where(YahooListing.listing_id.in_(held))
                .order_by(YahooListing.attempted_at.asc().nullsfirst(), YahooListing.listing_id)
                .with_for_update(of=YahooListing, skip_locked=True)
            )
        )
        jobs = []
        now = datetime.now(UTC)
        for row, listing, instrument in rows:
            if len(jobs) == 8:
                break
            if row.attempted_at and now - row.attempted_at < COOLDOWN:
                continue
            token = uuid4()
            row.attempted_at, row.lease = now, token
            jobs.append(
                (listing.id, token, row.symbol, listing.mic, listing.currency, instrument.kind)
            )

    # No database connection or transaction is held during HTTP.
    def fetch(job):
        try:
            return yahoo.lookup(*job[2:])
        except yahoo.YahooUnavailable:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(fetch, jobs))
    updated = failed = 0
    with session.begin():
        for job, answer in zip(jobs, answers, strict=True):
            row = session.get(YahooListing, job[0], with_for_update=True)
            if row is None or row.lease != job[1]:
                continue  # Configuration changed while the HTTP request was in flight.
            row.lease = None
            row.failed = answer is None
            if answer is None:
                failed += 1
                continue
            # An upstream replica returning an older quote must not roll the cache backwards.
            if row.quoted_at is None or answer.quoted_at >= row.quoted_at:
                row.price, row.quoted_at = answer.price, answer.quoted_at
                row.fetched_at = datetime.now(UTC)
                updated += 1
    return dict(updated=updated, failed=failed, cooldown_seconds=300)
