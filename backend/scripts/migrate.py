"""Bring the database schema up to date; run on every start before the API.

The base dhan_* tables were first created by the Django admin's migrations, so Alembic's history
alone can't build a fresh database. An empty database is built from the SQLAlchemy models plus the
database-level checks that only live in migrations, then stamped at head. Any database that already
has a schema just runs the remaining Alembic migrations.
"""

import asyncio
import importlib.util
import logging
import sys
from pathlib import Path

from sqlalchemy import inspect, text

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

import fastapi_app.models  # noqa: E402, F401
from fastapi_app.db.base import Base  # noqa: E402
from fastapi_app.db.session import engine  # noqa: E402

logger = logging.getLogger("scripts.migrate")

# Final form of the transaction-type check after the phase 13 split migration
TRANSACTION_TYPE_CHECK = "transaction_type IN ('expense', 'income', 'transfer', 'split')"


def _integrity_checks() -> list[tuple[str, str, str]]:
    path = next((BACKEND_DIR / "alembic" / "versions").glob("e5a6b7c8d9f0_*.py"))
    spec = importlib.util.spec_from_file_location("integrity_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [
        (table, name, TRANSACTION_TYPE_CHECK if name == "ck_dhan_transactions_type" else condition)
        for table, name, condition in module.CHECKS
    ]


async def _bootstrap_if_empty() -> bool:
    async with engine.begin() as conn:
        tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
        if "alembic_version" in tables or "users" in tables:
            return False
        await conn.run_sync(Base.metadata.create_all)
        for table, name, condition in _integrity_checks():
            await conn.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({condition})"))
        await conn.execute(text("CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))"))
    await engine.dispose()
    return True


def main() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    try:
        if asyncio.run(_bootstrap_if_empty()):
            print("Empty database: created schema from models and stamped Alembic head.")
            command.stamp(config, "head")
        else:
            command.upgrade(config, "head")
    except Exception as exc:
        print(f"Warning: Database migrations could not be run: {exc}")
        print("Continuing startup so web service and landing page remain accessible...")


if __name__ == "__main__":
    main()
