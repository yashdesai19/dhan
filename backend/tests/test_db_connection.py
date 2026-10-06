"""Test database configuration and models."""

import pytest

import fastapi_app.models  # noqa: F401
from fastapi_app.db.base import Base
from fastapi_app.db.session import check_db_connection, engine


def test_models_metadata_registered() -> None:
    """Verify that models are registered in Base.metadata."""
    table_names = Base.metadata.tables.keys()
    assert "system_checks" in table_names


def test_sqlalchemy_engine_configuration() -> None:
    """Verify that SQLAlchemy async engine is properly instantiated."""
    assert engine is not None
    assert str(engine.url).startswith("postgresql+asyncpg://")


@pytest.mark.asyncio
async def test_live_postgres_or_graceful_status() -> None:
    """Check connectivity to PostgreSQL via check_db_connection helper."""
    # When PostgreSQL is up, check_db_connection() returns True.
    # When PostgreSQL is down, check_db_connection() returns False safely without raising uncaught exceptions.
    is_connected = await check_db_connection()
    assert isinstance(is_connected, bool)
