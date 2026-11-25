from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.api.routes import router
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

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return JSONResponse(status_code=503, content={"detail": "Baza danych jest niedostępna."})

    application.include_router(router)
    return application


app = create_app()
