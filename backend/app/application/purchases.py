import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.purchase_contracts import PurchaseCorrection, PurchaseCreate, PurchaseResponse
from app.infrastructure.catalog import IUSQ_LISTING_ID
from app.infrastructure.models import (
    Account,
    AuditEvent,
    Instrument,
    Listing,
    Operation,
    PurchaseDetails,
)


class PurchaseError(Exception):
    def __init__(self, message: str, status_code: int = 404, *, field: str | None = None):
        self.message = message
        self.status_code = status_code
        self.field = field
        super().__init__(message)


def owned_account(session: Session, account_id: UUID, owner_id: UUID, *, lock=False):
    query = select(Account).where(Account.id == account_id, Account.owner_id == owner_id)
    if lock:
        query = query.with_for_update()
    account = session.scalar(query)
    if account is None:
        raise PurchaseError("Nie znaleziono rachunku.")
    return account


def supported_listing(session: Session, listing_id: UUID, owner_id: UUID):
    listing = session.get(Listing, listing_id)
    if listing is None:
        raise PurchaseError("Nie znaleziono obsługiwanego notowania.", 422)
    instrument = session.get(Instrument, listing.instrument_id)
    if instrument.kind == "STOCK" and instrument.owner_id != owner_id:
        raise PurchaseError("Nie znaleziono notowania.")
    stock = instrument.kind == "STOCK" and instrument.owner_id == owner_id
    etf = listing.id == IUSQ_LISTING_ID and instrument.owner_id is None
    if listing.currency not in {"EUR", "PLN", "USD"} or not (stock or etf):
        raise PurchaseError("Wybierz obsługiwane notowanie akcji lub IUSQ.", 422)
    return listing


def matching_currency(listing: Listing, currency: str):
    if listing.currency != currency:
        raise PurchaseError(
            "Waluta operacji musi być zgodna z walutą notowania.", 422, field="currency"
        )


def supported_account(session: Session, account: Account, listing: Listing):
    if (
        account.kind == "IKE_BONDS"
        and session.get(Instrument, listing.instrument_id).kind == "STOCK"
    ):
        raise PurchaseError("Wybierz rachunek inwestycyjny do ewidencji akcji.", 422)


def snapshot(operation: Operation, details: PurchaseDetails) -> dict[str, str]:
    return {
        "listing_id": str(operation.listing_id),
        "trade_date": operation.trade_date.isoformat(),
        "quantity": format(details.quantity, "f"),
        "unit_price": format(details.unit_price, "f"),
        "commission": format(details.commission, "f"),
        "currency": details.currency,
    }


def response(operation: Operation, details: PurchaseDetails, listing: Listing, instrument):
    return PurchaseResponse(
        id=operation.id,
        account_id=operation.account_id,
        listing_id=listing.id,
        symbol=listing.symbol,
        isin=instrument.isin,
        trade_date=operation.trade_date,
        quantity=details.quantity,
        unit_price=details.unit_price,
        commission=details.commission,
        currency=details.currency,
        revision=operation.revision,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
    )


def find_purchase(session: Session, account_id: UUID, purchase_id: UUID, *, lock=False):
    query = (
        select(Operation, PurchaseDetails, Listing, Instrument)
        .join(PurchaseDetails, PurchaseDetails.operation_id == Operation.id)
        .join(Listing, Listing.id == Operation.listing_id)
        .join(Instrument, Instrument.id == Listing.instrument_id)
        .where(Operation.account_id == account_id, Operation.id == purchase_id)
    )
    if lock:
        query = query.with_for_update(of=Operation)
    result = session.execute(query).one_or_none()
    if result is None:
        raise PurchaseError("Nie znaleziono zakupu.")
    return result


def fingerprint(data: PurchaseCreate) -> str:
    values = {
        "listing_id": str(data.listing_id),
        "trade_date": data.trade_date.isoformat(),
        "quantity": format(data.quantity.normalize(), "f"),
        "unit_price": format(data.unit_price.normalize(), "f"),
        "commission": format(data.commission.normalize(), "f"),
        "currency": data.currency,
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def add_audit_event(session: Session, operation, details, owner_id, *, before=None, reason=None):
    session.add(
        AuditEvent(
            operation_id=operation.id,
            owner_id=owner_id,
            revision=operation.revision,
            kind="CREATE" if before is None else "CORRECT",
            reason=reason,
            before=before,
            after=snapshot(operation, details),
        )
    )


def create_purchase(
    session: Session, owner_id: UUID, account_id: UUID, data: PurchaseCreate
) -> tuple[PurchaseResponse, bool]:
    with session.begin():
        account = owned_account(session, account_id, owner_id, lock=True)
        listing = supported_listing(session, data.listing_id, owner_id)
        matching_currency(listing, data.currency)
        supported_account(session, account, listing)
        digest = fingerprint(data)
        existing = session.scalar(
            select(Operation).where(
                Operation.account_id == account_id, Operation.request_id == data.request_id
            )
        )
        if existing is not None:
            if existing.request_hash != digest:
                raise PurchaseError("Identyfikator zapisu był już użyty dla innych danych.", 409)
            return response(*find_purchase(session, account_id, existing.id)), False
        operation = Operation(
            account_id=account_id,
            listing_id=listing.id,
            kind="PURCHASE",
            trade_date=data.trade_date,
            revision=1,
            request_id=data.request_id,
            request_hash=digest,
        )
        session.add(operation)
        session.flush()
        details = PurchaseDetails(
            operation_id=operation.id,
            quantity=data.quantity,
            unit_price=data.unit_price,
            commission=data.commission,
            currency=data.currency,
        )
        session.add(details)
        session.flush()
        session.refresh(details)
        add_audit_event(session, operation, details, owner_id)
        instrument = session.get(Instrument, listing.instrument_id)
        return response(operation, details, listing, instrument), True


def correct_purchase(
    session: Session,
    owner_id: UUID,
    account_id: UUID,
    purchase_id: UUID,
    data: PurchaseCorrection,
) -> PurchaseResponse:
    with session.begin():
        account = owned_account(session, account_id, owner_id, lock=True)
        operation, details, _, _ = find_purchase(session, account_id, purchase_id, lock=True)
        if operation.revision != data.expected_revision:
            raise PurchaseError(
                "Zakup został już zmieniony. Odśwież historię i spróbuj ponownie.", 409
            )
        listing = supported_listing(session, data.listing_id, owner_id)
        matching_currency(listing, data.currency)
        supported_account(session, account, listing)
        before = snapshot(operation, details)
        if operation.listing_id != listing.id:
            raise PurchaseError("Korekta nie może zmienić notowania zakupu.", 422)
        operation.listing_id = listing.id
        operation.trade_date = data.trade_date
        operation.revision += 1
        details.quantity = data.quantity
        details.unit_price = data.unit_price
        details.commission = data.commission
        details.currency = data.currency
        session.flush()
        session.refresh(operation)
        session.refresh(details)
        add_audit_event(session, operation, details, owner_id, before=before, reason=data.reason)
        instrument = session.get(Instrument, listing.instrument_id)
        return response(operation, details, listing, instrument)


def get_purchases(session: Session, owner_id: UUID, account_id: UUID):
    owned_account(session, account_id, owner_id)
    rows = session.execute(
        select(Operation, PurchaseDetails, Listing, Instrument)
        .join(PurchaseDetails, PurchaseDetails.operation_id == Operation.id)
        .join(Listing, Listing.id == Operation.listing_id)
        .join(Instrument, Instrument.id == Listing.instrument_id)
        .where(Operation.account_id == account_id)
        .order_by(Operation.trade_date.desc(), Operation.created_at.desc(), Operation.id)
    )
    return [response(*row) for row in rows]


def get_audit(session: Session, owner_id: UUID, account_id: UUID, purchase_id: UUID):
    owned_account(session, account_id, owner_id)
    find_purchase(session, account_id, purchase_id)
    return list(
        session.scalars(
            select(AuditEvent)
            .where(AuditEvent.operation_id == purchase_id, AuditEvent.owner_id == owner_id)
            .order_by(AuditEvent.revision)
        )
    )
