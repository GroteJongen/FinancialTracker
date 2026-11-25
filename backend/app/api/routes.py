from collections.abc import Generator
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.accounts import list_accounts
from app.application.purchase_contracts import (
    AuditResponse, ListingResponse, PurchaseCorrection, PurchaseCreate, PurchaseResponse,
)
from app.application.purchases import (
    correct_purchase, create_purchase, get_audit, get_purchases,
)
from app.infrastructure.models import Instrument, Listing

router = APIRouter(prefix="/api")


def get_session(request: Request) -> Generator[Session]:
    with request.app.state.session_factory() as session:
        yield session


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    kind: str
    currency: str


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", response_model=None)
def ready(request: Request):
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            if revision != request.app.state.schema_revision:
                return JSONResponse(status_code=503, content={"status": "unavailable"})
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok", "database": "ok"}


@router.get("/accounts", response_model=list[AccountResponse])
def accounts(request: Request, session: Session = Depends(get_session)):
    return list_accounts(session, request.app.state.settings.local_owner_id)


@router.get("/listings", response_model=list[ListingResponse])
def listings(session: Session = Depends(get_session)):
    rows = session.execute(select(Listing, Instrument).join(Instrument))
    return [
        ListingResponse(
            id=listing.id, name=instrument.name, symbol=listing.symbol,
            isin=instrument.isin, mic=listing.mic, currency=listing.currency,
        )
        for listing, instrument in rows
    ]


@router.get("/accounts/{account_id}/purchases", response_model=list[PurchaseResponse])
def purchases(account_id: UUID, request: Request, session: Session = Depends(get_session)):
    return get_purchases(session, request.app.state.settings.local_owner_id, account_id)


@router.post("/accounts/{account_id}/purchases", response_model=PurchaseResponse, status_code=201)
def add_purchase(
    account_id: UUID, data: PurchaseCreate, request: Request, response: Response,
    session: Session = Depends(get_session),
):
    result, created = create_purchase(
        session, request.app.state.settings.local_owner_id, account_id, data
    )
    if not created:
        response.status_code = 200
    return result


@router.put("/accounts/{account_id}/purchases/{purchase_id}", response_model=PurchaseResponse)
def edit_purchase(
    account_id: UUID, purchase_id: UUID, data: PurchaseCorrection, request: Request,
    session: Session = Depends(get_session),
):
    return correct_purchase(
        session, request.app.state.settings.local_owner_id, account_id, purchase_id, data
    )


@router.get(
    "/accounts/{account_id}/purchases/{purchase_id}/audit", response_model=list[AuditResponse]
)
def purchase_audit(
    account_id: UUID, purchase_id: UUID, request: Request, session: Session = Depends(get_session),
):
    return get_audit(
        session, request.app.state.settings.local_owner_id, account_id, purchase_id
    )
