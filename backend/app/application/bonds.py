import hashlib
import json
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.application.bond_contracts import (
    BondAccountCreate,
    BondCorrection,
    BondCreate,
    BondFields,
    BondResponse,
)
from app.application.purchases import PurchaseError, owned_account
from app.domain.bonds import BOND_TERMS, purchase_cost
from app.infrastructure.models import Account, BondAuditEvent, BondIssue, BondPurchase, Owner


def create_bond_account(session: Session, owner_id: UUID, data: BondAccountCreate):
    with session.begin():
        session.execute(
            insert(Owner)
            .values(id=owner_id, name="Użytkownik lokalny")
            .on_conflict_do_nothing(index_elements=["id"])
        )
        lock_owner(session, owner_id)
        existing = session.scalar(
            select(Account).where(Account.owner_id == owner_id, Account.name == data.name)
        )
        if existing is not None:
            if existing.kind != data.kind or existing.currency != "PLN":
                raise PurchaseError("Rachunek o tej nazwie ma już inny typ lub walutę.", 409)
            return dict(
                id=existing.id, name=existing.name, kind=existing.kind, currency=existing.currency
            ), False
        account = Account(owner_id=owner_id, name=data.name, kind=data.kind, currency="PLN")
        session.add(account)
        session.flush()
        # Return detached response values before commit expires the ORM attributes.
        result = dict(
            id=account.id, name=account.name, kind=account.kind, currency=account.currency
        )
        return result, True


def lock_owner(session: Session, owner_id: UUID):
    # Serialize owner commands while allowing FK KEY SHARE checks from account writers.
    session.scalar(select(Owner).where(Owner.id == owner_id).with_for_update(key_share=True))


def bond_account(session: Session, account_id: UUID, owner_id: UUID, *, lock=False):
    account = owned_account(session, account_id, owner_id, lock=lock)
    if account.currency != "PLN" or account.kind not in {"STANDARD", "IKE_BONDS", "IKZE"}:
        raise PurchaseError("Wybierz rachunek obligacji w PLN: zwykły, IKE lub IKZE.", 422)
    return account


def canonical(value):
    return format(value.normalize(), "f") if isinstance(value, Decimal) else value


def digest(values) -> str:
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def issue_for(session: Session, owner_id: UUID, data: BondFields):
    values = {
        "series": data.series,
        "annual_rate": canonical(data.annual_rate),
        "margin": canonical(data.margin),
        "source_url": data.source_url,
    }
    version = digest(values)
    issue = session.scalar(
        select(BondIssue).where(
            BondIssue.owner_id == owner_id,
            BondIssue.series == data.series,
            BondIssue.terms_version == version,
        )
    )
    if issue is None:
        issue = BondIssue(
            owner_id=owner_id,
            series=data.series,
            bond_type=data.series[:3],
            terms_version=version,
            annual_rate=data.annual_rate,
            margin=data.margin,
            source_url=data.source_url,
        )
        session.add(issue)
        session.flush()
        session.refresh(issue)
    return issue


def response(purchase: BondPurchase, issue: BondIssue) -> BondResponse:
    return BondResponse(
        id=purchase.id,
        account_id=purchase.account_id,
        issue_id=issue.id,
        terms_version=issue.terms_version,
        series=issue.series,
        bond_type=issue.bond_type,
        term_years=BOND_TERMS[issue.bond_type],
        trade_date=purchase.trade_date,
        quantity=purchase.quantity,
        unit_price=purchase.unit_price,
        cost=purchase_cost(purchase.quantity, purchase.unit_price),
        annual_rate=issue.annual_rate,
        margin=issue.margin,
        source_url=issue.source_url,
        revision=purchase.revision,
        created_at=purchase.created_at,
    )


def snapshot(purchase: BondPurchase, issue: BondIssue) -> dict[str, str]:
    return {
        key: "" if value is None else str(value)
        for key, value in response(purchase, issue).model_dump(mode="json").items()
        if key not in {"id", "account_id", "created_at", "revision", "cost"}
    }


def find_purchase(session: Session, account_id: UUID, purchase_id: UUID):
    row = session.execute(
        select(BondPurchase, BondIssue)
        .join(BondIssue, BondIssue.id == BondPurchase.issue_id)
        .where(BondPurchase.account_id == account_id, BondPurchase.id == purchase_id)
    ).one_or_none()
    if row is None:
        raise PurchaseError("Nie znaleziono zakupu obligacji.")
    return row


def audit(session: Session, purchase, issue, owner_id, *, before=None, reason=None):
    session.add(
        BondAuditEvent(
            purchase_id=purchase.id,
            owner_id=owner_id,
            revision=purchase.revision,
            kind="CREATE" if before is None else "CORRECT",
            before=before,
            after=snapshot(purchase, issue),
            reason=reason,
        )
    )


def create_bond_purchase(session: Session, owner_id: UUID, account_id: UUID, data: BondCreate):
    with session.begin():
        lock_owner(session, owner_id)
        bond_account(session, account_id, owner_id, lock=True)
        values = {
            key: canonical(value)
            for key, value in data.model_dump(exclude={"request_id", "trade_date"}).items()
        }
        request_hash = digest(values | {"trade_date": data.trade_date.isoformat()})
        existing = session.scalar(
            select(BondPurchase).where(
                BondPurchase.account_id == account_id, BondPurchase.request_id == data.request_id
            )
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise PurchaseError("Identyfikator zapisu był już użyty dla innych danych.", 409)
            return response(*find_purchase(session, account_id, existing.id)), False
        issue = issue_for(session, owner_id, data)
        purchase = BondPurchase(
            account_id=account_id,
            issue_id=issue.id,
            trade_date=data.trade_date,
            quantity=data.quantity,
            unit_price=data.unit_price,
            revision=1,
            request_id=data.request_id,
            request_hash=request_hash,
        )
        session.add(purchase)
        session.flush()
        session.refresh(purchase)
        audit(session, purchase, issue, owner_id)
        return response(purchase, issue), True


def correct_bond_purchase(
    session: Session, owner_id: UUID, account_id: UUID, purchase_id: UUID, data: BondCorrection
):
    with session.begin():
        lock_owner(session, owner_id)
        bond_account(session, account_id, owner_id, lock=True)
        purchase, old_issue = find_purchase(session, account_id, purchase_id)
        if purchase.revision != data.expected_revision:
            raise PurchaseError("Zakup zmienił się. Odśwież historię przed korektą.", 409)
        before = snapshot(purchase, old_issue)
        issue = issue_for(session, owner_id, data)
        purchase.issue_id = issue.id
        purchase.trade_date = data.trade_date
        purchase.quantity = data.quantity
        purchase.unit_price = data.unit_price
        purchase.revision += 1
        session.flush()
        session.refresh(purchase)
        audit(session, purchase, issue, owner_id, before=before, reason=data.reason)
        return response(purchase, issue)


def get_bond_purchases(session: Session, owner_id: UUID, account_id: UUID):
    bond_account(session, account_id, owner_id)
    rows = session.execute(
        select(BondPurchase, BondIssue)
        .join(BondIssue, BondIssue.id == BondPurchase.issue_id)
        .where(BondPurchase.account_id == account_id)
        .order_by(BondPurchase.trade_date.desc(), BondPurchase.created_at.desc(), BondPurchase.id)
    )
    return [response(*row) for row in rows]


def get_bond_audit(session: Session, owner_id: UUID, account_id: UUID, purchase_id: UUID):
    bond_account(session, account_id, owner_id)
    find_purchase(session, account_id, purchase_id)
    return list(
        session.scalars(
            select(BondAuditEvent)
            .where(BondAuditEvent.purchase_id == purchase_id, BondAuditEvent.owner_id == owner_id)
            .order_by(BondAuditEvent.revision)
        )
    )
