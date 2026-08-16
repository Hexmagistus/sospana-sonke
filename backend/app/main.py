"""Sospana Sonke API entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import init_db
from app.api import (
    routes_auth, routes_companies, routes_profile, routes_cv, routes_vacancies, routes_matches,
    routes_documents, routes_applications, routes_subscription, routes_dashboard,
    routes_notifications,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # First-boot bootstrap (seed companies + create admin) when configured.
    try:
        from app.db.session import SessionLocal
        from app.services.bootstrap import bootstrap
        db = SessionLocal()
        try:
            bootstrap(db)
        finally:
            db.close()
    except Exception:
        pass  # never let optional bootstrap block startup
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version="0.1.0",
        description="AI-powered job discovery, CV tailoring and application platform (Phase 1 foundation).",
        lifespan=lifespan,
    )

    # CORS: allowed browser origins come from config (set the frontend URL in prod).
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}

    app.include_router(routes_auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_companies.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_profile.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_cv.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_vacancies.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_matches.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_documents.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_applications.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_subscription.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_dashboard.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_notifications.router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
