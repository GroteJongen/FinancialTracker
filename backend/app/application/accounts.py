from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Account


def list_accounts(session: Session, owner_id: UUID) -> list[Account]:
    return list(
        session.scalars(
            select(Account).where(Account.owner_id == owner_id).order_by(Account.name, Account.id)
        )
    )

