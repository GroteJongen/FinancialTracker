from collections.abc import Generator
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.accounts import list_accounts

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
            if revision != "0001":
                return JSONResponse(status_code=503, content={"status": "unavailable"})
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok", "database": "ok"}


@router.get("/accounts", response_model=list[AccountResponse])
def accounts(request: Request, session: Session = Depends(get_session)):
    return list_accounts(session, request.app.state.settings.local_owner_id)
