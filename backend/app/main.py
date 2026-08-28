"""Sospana Sonke API entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import init_db
from app.api import (
    routes_auth, routes_companies, routes_profile, routes_cv, routes_vacancies, routes_matches,
    routes_documents, routes_applications, routes_subscription, routes_dashboard,
    routes_notifications, routes_cron,
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
    # Trailing slashes/whitespace are stripped so a stray "/" can't break matching.
    origins = [o.strip().rstrip("/") for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # Always allow this project's Vercel site and its preview deployments,
        # so the frontend works even if CORS_ORIGINS is unset or mistyped.
        allow_origin_regex=r"https://sospana-sonke[a-z0-9-]*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        # Harmless on plain HTTP (browsers only honour HSTS on https responses);
        # Render terminates TLS in front of this app, so this covers the real traffic.
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

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
    app.include_router(routes_cron.router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
