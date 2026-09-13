"""Sospana Sonke API entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.db.session import init_db
from app.api import (
    routes_auth, routes_companies, routes_profile, routes_cv, routes_vacancies, routes_matches,
    routes_documents, routes_applications, routes_subscription, routes_donation, routes_dashboard,
    routes_notifications, routes_cron, routes_tailor, routes_watches,
)

# Set up logging (and Sentry, if SENTRY_DSN is configured) before anything else
# runs, so startup itself — and every request/job after it — is observable.
configure_logging()
logger = logging.getLogger(__name__)


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
        logger.exception("Optional startup bootstrap failed; continuing without it")
    yield


def create_app() -> FastAPI:
    # In production, hide the interactive API docs and raw OpenAPI schema: they
    # map out every endpoint, request/response shape and internal route name for
    # anyone who finds the URL. Still fully available in dev/staging for testing.
    is_production = settings.ENV == "production"
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version="0.1.0",
        description="AI-powered job discovery, CV tailoring and application platform (Phase 1 foundation).",
        lifespan=lifespan,
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )

    # Rate limiting (brute-force / abuse protection on sensitive endpoints -- see
    # app/core/rate_limit.py and the @limiter.limit(...) decorators in routes_auth.py).
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

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
    async def log_unhandled_exceptions(request, call_next):
        # Outermost middleware (registered after add_security_headers, so it
        # wraps it): catches anything that reaches here unhandled from a route,
        # dependency, or another middleware, logs it with request context, then
        # re-raises so FastAPI/Starlette's normal 500 handling is unchanged.
        # Without this, an error outside the job runner or the routes with their
        # own try/except left literally no trace anywhere.
        try:
            return await call_next(request)
        except Exception:
            logging.getLogger("app.request").exception(
                "Unhandled exception on %s %s", request.method, request.url.path)
            raise

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
        # This API only ever serves JSON, never HTML/JS meant to run in a browser
        # (docs UI aside, and that's disabled in production), so a locked-down CSP
        # is free security with no functionality cost. Skip it on the docs routes
        # in non-production so Swagger/Redoc's own scripts still load for testing.
        if request.url.path not in ("/docs", "/redoc", "/openapi.json"):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
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
    app.include_router(routes_donation.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_dashboard.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_notifications.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_cron.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_tailor.router, prefix=settings.API_V1_PREFIX)
    app.include_router(routes_watches.router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
