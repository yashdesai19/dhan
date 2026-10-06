"""FastAPI Application Entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fastapi_app.ai.providers import AIProviderUnavailable
from fastapi_app.api.v1.endpoints import (
    accounts,
    ai,
    auth,
    budgets,
    categories,
    goals,
    net_worth,
    recurring,
    reports,
    splits,
    transactions,
)
from fastapi_app.api.v1.router import api_v1_router
from fastapi_app.core.config import Settings, settings
from fastapi_app.db.session import check_db_connection, engine
from fastapi_app.schemas.health import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fastapi_app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} ({settings.ENVIRONMENT})")
    try:
        is_db_connected = await check_db_connection()
        if is_db_connected:
            logger.info("Successfully connected to PostgreSQL database.")
        else:
            logger.warning("Could not establish immediate PostgreSQL connection at startup.")
    except Exception as exc:
        logger.warning(f"Database check during startup encountered error: {exc}")

    yield

    logger.info("Shutting down application, closing database connections...")
    await engine.dispose()
    logger.info("Application shutdown complete.")


def enforce_production_settings(config: Settings) -> None:
    """Refuses to start a production deployment with development secrets or debug output."""
    if config.is_production and (problems := config.production_problems()):
        raise RuntimeError("Refusing to start in production: " + "; ".join(problems))


enforce_production_settings(settings)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    # Debug responses include stack traces; never in production
    debug=settings.DEBUG and not settings.is_production,
    lifespan=lifespan,
    # The API description is a map for attackers too; development only
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# Configure CORS. Auth is a bearer header, not cookies, so credentials are only needed for
# named origins; browsers must never be told a wildcard origin may send credentials.
_cors_wildcard = "*" in settings.FASTAPI_CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FASTAPI_CORS_ORIGINS,
    allow_credentials=not _cors_wildcard,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Response headers that stop sniffing, framing, referrer leaks and caching of money data."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Logs the failure server-side; the client only learns that something went wrong."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


@app.exception_handler(AIProviderUnavailable)
async def ai_unavailable_handler(request: Request, exc: AIProviderUnavailable) -> JSONResponse:
    """The AI provider couldn't be used; nothing was saved, so the client can retry."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(exc)}
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Root health check endpoint returning { 'status': 'ok' }."""
    return HealthResponse(status="ok")


# Mount direct root endpoints (/auth, /accounts, /categories, /transactions, /budgets, /groups, /splits, /settlements, /people, /goals, /recurring, /reports, /net-worth, /ai)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(splits.groups_router)
app.include_router(splits.splits_router)
app.include_router(splits.settlements_router)
app.include_router(splits.people_router)
app.include_router(goals.router)
app.include_router(recurring.router)
app.include_router(reports.router)
app.include_router(net_worth.router)
app.include_router(ai.router)

# Mount versioned API routes (/api/v1/...)
app.include_router(api_v1_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fastapi_app.main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=settings.DEBUG,
    )
