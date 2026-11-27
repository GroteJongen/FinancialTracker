from collections.abc import Generator
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.accounts import list_accounts
from app.application.bond_contracts import (
    BondAccountCreate,
    BondCorrection,
    BondCreate,
    BondResponse,
)
from app.application.bonds import (
    correct_bond_purchase,
    create_bond_account,
    create_bond_purchase,
    get_bond_audit,
    get_bond_purchases,
)
from app.application.purchase_contracts import (
    AuditResponse,
    ListingResponse,
    PurchaseCorrection,
    PurchaseCreate,
    PurchaseResponse,
)
from app.application.purchases import (
    correct_purchase,
    create_purchase,
    get_audit,
    get_purchases,
)
from app.application.stock_contracts import InvestmentAccountCreate, StockCreate
from app.application.stocks import catalogue, create_investment_account, create_stock
from app.application.valuation_contracts import PriceCreate, PriceResponse, ValuationResponse
from app.application.valuations import create_price, get_valuation
from app.infrastructure.catalog import IUSQ_LISTING_ID

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
def listings(
    request: Request, kind: Literal["ETF", "STOCK"] = "ETF", session: Session = Depends(get_session)
):
    return catalogue(session, request.app.state.settings.local_owner_id, kind)


@router.post("/stocks", response_model=ListingResponse, status_code=201)
def add_stock(
    data: StockCreate, request: Request, response: Response, session: Session = Depends(get_session)
):
    result, created = create_stock(session, request.app.state.settings.local_owner_id, data)
    if not created:
        response.status_code = 200
    return result


@router.post("/investment-accounts", response_model=AccountResponse, status_code=201)
def add_investment_account(
    data: InvestmentAccountCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    result, created = create_investment_account(
        session, request.app.state.settings.local_owner_id, data
    )
    if not created:
        response.status_code = 200
    return result


@router.get("/accounts/{account_id}/purchases", response_model=list[PurchaseResponse])
def purchases(account_id: UUID, request: Request, session: Session = Depends(get_session)):
    return get_purchases(session, request.app.state.settings.local_owner_id, account_id)


@router.post("/accounts/{account_id}/purchases", response_model=PurchaseResponse, status_code=201)
def add_purchase(
    account_id: UUID,
    data: PurchaseCreate,
    request: Request,
    response: Response,
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
    account_id: UUID,
    purchase_id: UUID,
    data: PurchaseCorrection,
    request: Request,
    session: Session = Depends(get_session),
):
    return correct_purchase(
        session, request.app.state.settings.local_owner_id, account_id, purchase_id, data
    )


@router.get(
    "/accounts/{account_id}/purchases/{purchase_id}/audit", response_model=list[AuditResponse]
)
def purchase_audit(
    account_id: UUID,
    purchase_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    return get_audit(session, request.app.state.settings.local_owner_id, account_id, purchase_id)


@router.get("/accounts/{account_id}/valuation", response_model=ValuationResponse)
def valuation(
    account_id: UUID,
    request: Request,
    listing_id: UUID = IUSQ_LISTING_ID,
    session: Session = Depends(get_session),
):
    return get_valuation(session, request.app.state.settings.local_owner_id, account_id, listing_id)


@router.post("/accounts/{account_id}/prices", response_model=PriceResponse, status_code=201)
def add_price(
    account_id: UUID,
    data: PriceCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    result, created = create_price(
        session, request.app.state.settings.local_owner_id, account_id, data
    )
    if not created:
        response.status_code = 200
    return result


@router.post("/bond-accounts", response_model=AccountResponse, status_code=201)
def add_bond_account(
    data: BondAccountCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    result, created = create_bond_account(session, request.app.state.settings.local_owner_id, data)
    if not created:
        response.status_code = 200
    return result


@router.get("/accounts/{account_id}/bonds", response_model=list[BondResponse])
def bonds(account_id: UUID, request: Request, session: Session = Depends(get_session)):
    return get_bond_purchases(session, request.app.state.settings.local_owner_id, account_id)


@router.post("/accounts/{account_id}/bonds", response_model=BondResponse, status_code=201)
def add_bond(
    account_id: UUID,
    data: BondCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    result, created = create_bond_purchase(
        session, request.app.state.settings.local_owner_id, account_id, data
    )
    if not created:
        response.status_code = 200
    return result


@router.put("/accounts/{account_id}/bonds/{purchase_id}", response_model=BondResponse)
def edit_bond(
    account_id: UUID,
    purchase_id: UUID,
    data: BondCorrection,
    request: Request,
    session: Session = Depends(get_session),
):
    return correct_bond_purchase(
        session, request.app.state.settings.local_owner_id, account_id, purchase_id, data
    )


@router.get("/accounts/{account_id}/bonds/{purchase_id}/audit", response_model=list[AuditResponse])
def bond_audit(
    account_id: UUID,
    purchase_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    return get_bond_audit(
        session, request.app.state.settings.local_owner_id, account_id, purchase_id
    )
