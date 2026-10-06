"""Verify that FastAPI (SQLAlchemy) and Django connect to the exact same PostgreSQL database."""

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

# Setup paths
backend_dir = Path(__file__).resolve().parent.parent
django_dir = backend_dir / "django_admin"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(django_dir) not in sys.path:
    sys.path.insert(0, str(django_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import django

django.setup()

from apps.core.models import AdminAuditLog
from django.db import connection as django_connection

from fastapi_app.db.session import check_db_connection, engine


@pytest.mark.asyncio
async def test_fastapi_and_django_shared_postgres_database() -> None:
    """Verify that FastAPI and Django are connected to the same PostgreSQL database."""
    # 1. FastAPI connection via SQLAlchemy asyncpg
    is_fastapi_db_ok = await check_db_connection()
    assert is_fastapi_db_ok is True, "FastAPI failed to connect to PostgreSQL"

    # 2. Django connection via psycopg
    with django_connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
        assert row is not None and row[0] == 1, "Django failed to connect to PostgreSQL"

    # 3. Create record using Django ORM
    test_action = "health_verification_check"
    log = AdminAuditLog.objects.create(action=test_action, performed_by="automated_test")
    assert log.id is not None

    # 4. Read that exact record using FastAPI's SQLAlchemy async engine
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, action, performed_by FROM django_admin_audit_logs WHERE id = :log_id"),
            {"log_id": log.id},
        )
        fetched = result.fetchone()
        assert fetched is not None
        assert fetched[0] == log.id
        assert fetched[1] == test_action
        assert fetched[2] == "automated_test"

    # Clean up test record
    log.delete()
