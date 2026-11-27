from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.application.bonds import lock_owner
from app.application.purchases import PurchaseError
from app.application.stocks import ensure_owner
from app.infrastructure.models import Account, PortfolioAccount, PortfolioGroup


class GroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    account_ids: list[UUID] = Field(max_length=500)

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("account_ids")
    @classmethod
    def unique_accounts(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Rachunek moze wystapic w portfelu tylko raz.")
        return value


class GroupUpdate(GroupCreate):
    expected_revision: int = Field(strict=True, ge=1)


def owned_group(session, owner_id, group_id):
    group = session.scalar(
        select(PortfolioGroup).where(
            PortfolioGroup.id == group_id, PortfolioGroup.owner_id == owner_id
        )
    )
    if group is None:
        raise PurchaseError("Nie znaleziono portfela.")
    return group


def response(session, group):
    return dict(
        id=str(group.id),
        name=group.name,
        revision=group.revision,
        account_ids=[
            str(value)
            for value in session.scalars(
                select(PortfolioAccount.account_id)
                .where(PortfolioAccount.portfolio_id == group.id)
                .order_by(PortfolioAccount.account_id)
            )
        ],
    )


def list_groups(session: Session, owner_id: UUID):
    with session.begin():
        lock_owner(session, owner_id)
        return [
            response(session, row)
            for row in session.scalars(
                select(PortfolioGroup)
                .where(PortfolioGroup.owner_id == owner_id)
                .order_by(PortfolioGroup.name, PortfolioGroup.id)
            )
        ]


def save_group(session: Session, owner_id: UUID, data: GroupCreate, group_id=None):
    with session.begin():
        ensure_owner(session, owner_id)
        accounts = set(
            session.scalars(
                select(Account.id).where(
                    Account.owner_id == owner_id, Account.id.in_(data.account_ids)
                )
            )
        )
        if accounts != set(data.account_ids):
            raise PurchaseError("Nie znaleziono jednego z rachunkow.")
        existing = session.scalar(
            select(PortfolioGroup).where(
                PortfolioGroup.owner_id == owner_id, PortfolioGroup.name == data.name
            )
        )
        if group_id is None and existing:
            result = response(session, existing)
            if set(result["account_ids"]) != {str(value) for value in data.account_ids}:
                raise PurchaseError("Portfel o tej nazwie ma juz inne rachunki.", 409)
            return result, False
        if group_id is None:
            group = PortfolioGroup(owner_id=owner_id, name=data.name)
            session.add(group)
            session.flush()
        else:
            group = owned_group(session, owner_id, group_id)
            if existing and existing.id != group.id:
                raise PurchaseError("Nazwa portfela jest juz zajeta.", 409)
            if group.revision != data.expected_revision:
                raise PurchaseError("Portfel zostal zmieniony. Odswiez liste.", 409)
            group.name = data.name
            group.revision += 1
            session.execute(
                delete(PortfolioAccount).where(PortfolioAccount.portfolio_id == group.id)
            )
        for account_id in data.account_ids:
            session.add(PortfolioAccount(portfolio_id=group.id, account_id=account_id))
        session.flush()
        return response(session, group), group_id is None
