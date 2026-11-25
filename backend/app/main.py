from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.api.routes import router
from app.application.purchases import PurchaseError
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database import make_engine


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    settings = settings or get_settings()
    owns_engine = engine is None
    database_engine = engine if engine is not None else make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        yield
        if owns_engine:
            database_engine.dispose()

    application = FastAPI(title="FinancialTracker", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    application.state.engine = database_engine
    application.state.session_factory = sessionmaker(database_engine)
    migration_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    application.state.schema_revision = ScriptDirectory.from_config(
        migration_config
    ).get_current_head()

    @application.exception_handler(PurchaseError)
    async def purchase_error(request: Request, exc: PurchaseError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            field = str(error["loc"][-1])
            if error["type"] == "value_error":
                message = error["msg"].removeprefix("Value error, ")
            elif field == "currency":
                message = "Dla tego zakupu wybierz EUR."
            elif error["type"] == "extra_forbidden":
                message = "To pole nie jest obsługiwane."
            elif error["type"] == "missing":
                message = "Uzupełnij wymagane pole."
            elif field == "reason":
                message = "Podaj powód korekty (od 1 do 500 znaków)."
            else:
                message = "Podaj poprawną wartość."
            errors.append({"field": field, "message": message})
        return JSONResponse(
            status_code=422, content={"detail": "Sprawdź dane formularza.", "errors": errors}
        )

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return JSONResponse(status_code=503, content={"detail": "Baza danych jest niedostępna."})

    application.include_router(router)
    return application


app = create_app()
