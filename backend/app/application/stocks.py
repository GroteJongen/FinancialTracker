from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.application.bonds import lock_owner
from app.application.purchase_contracts import ListingResponse
from app.application.purchases import PurchaseError
from app.application.stock_contracts import InvestmentAccountCreate, StockCreate
from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.infrastructure.models import Account, Instrument, Listing, Owner


def listing_response(listing: Listing, instrument: Instrument):
    return ListingResponse(
        id=listing.id,
        name=instrument.name,
        symbol=listing.symbol,
        isin=instrument.isin,
        mic=listing.mic,
        currency=listing.currency,
        kind=instrument.kind,
    )


def catalogue(session: Session, owner_id: UUID, kind: str):
    query = (
        select(Listing, Instrument)
        .join(Instrument)
        .where(or_(Instrument.owner_id == owner_id, Listing.id == IUSQ_LISTING_ID))
    )
    if kind != "ALL":
        query = query.where(Instrument.kind == kind)
    return [
        listing_response(*row)
        for row in session.execute(query.order_by(Instrument.name, Listing.mic, Listing.currency))
    ]


def ensure_owner(session: Session, owner_id: UUID):
    session.execute(
        insert(Owner)
        .values(id=owner_id, name="Użytkownik lokalny")
        .on_conflict_do_nothing(index_elements=["id"])
    )
    lock_owner(session, owner_id)


def create_stock(session: Session, owner_id: UUID, data: StockCreate):
    kind = getattr(data, "kind", "STOCK")
    with session.begin():
        ensure_owner(session, owner_id)
        existing = session.execute(
            select(Listing, Instrument)
            .join(Instrument)
            .where(
                Instrument.owner_id == owner_id,
                Instrument.kind == kind,
                Listing.symbol == data.symbol,
                Listing.mic == data.mic,
                Listing.currency == data.currency,
            )
        ).one_or_none()
        if existing:
            listing, instrument = existing
            if instrument.name != data.name or instrument.isin != data.isin:
                raise PurchaseError("To notowanie już istnieje z innymi danymi spółki.", 409)
            return listing_response(listing, instrument), False
        instrument = (
            session.scalar(
                select(Instrument).where(
                    Instrument.owner_id == owner_id, Instrument.isin == data.isin
                )
            )
            if data.isin
            else None
        )
        if instrument is not None:
            if instrument.kind != kind or instrument.name != data.name:
                raise PurchaseError(
                    "Ten ISIN jest już przypisany do innych danych instrumentu.", 409
                )
            duplicate = session.scalar(
                select(Listing).where(
                    Listing.instrument_id == instrument.id,
                    Listing.mic == data.mic,
                    Listing.currency == data.currency,
                )
            )
            if duplicate:
                raise PurchaseError(
                    "Instrument ma już notowanie na tej giełdzie w tej walucie.", 409
                )
        else:
            instrument = Instrument(
                owner_id=owner_id, name=data.name, isin=data.isin, kind=kind, distribution=None
            )
            session.add(instrument)
            session.flush()
        listing = Listing(
            instrument_id=instrument.id, symbol=data.symbol, mic=data.mic, currency=data.currency
        )
        session.add(listing)
        session.flush()
        return listing_response(listing, instrument), True


def create_investment_account(session: Session, owner_id: UUID, data: InvestmentAccountCreate):
    with session.begin():
        ensure_owner(session, owner_id)
        account = session.scalar(
            select(Account).where(Account.owner_id == owner_id, Account.name == data.name)
        )
        created = account is None
        if account is not None and (account.kind != data.kind or account.currency != data.currency):
            raise PurchaseError("Rachunek o tej nazwie ma już inny typ lub walutę.", 409)
        if account is None:
            account = Account(
                owner_id=owner_id, name=data.name, kind=data.kind, currency=data.currency
            )
            session.add(account)
            session.flush()
        return dict(
            id=account.id, name=account.name, kind=account.kind, currency=account.currency
        ), created
