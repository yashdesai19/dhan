"""Bring the database schema up to date; run on every start before the API.

The base dhan_* tables were first created by the Django admin's migrations, so Alembic's history
alone can't build a fresh database. An empty database is built from the SQLAlchemy models plus the
database-level checks that only live in migrations, then stamped at head. Any database that already
has a schema just runs the remaining Alembic migrations.
"""

import asyncio
import importlib.util
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
    print("[MIGRATE] Connecting to PostgreSQL database...", flush=True)
    async with engine.begin() as conn:
        tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
        print(f"[MIGRATE] Connected successfully! Found {len(tables)} tables.", flush=True)
        if "alembic_version" in tables or "users" in tables:
            print("[MIGRATE] Database schema already exists; skipping bootstrap.", flush=True)
            return False
        print("[MIGRATE] Empty database detected. Bootstrapping schema from models...", flush=True)
        await conn.run_sync(Base.metadata.create_all)
        print("[MIGRATE] Applying integrity checks...", flush=True)
        for table, name, condition in _integrity_checks():
            await conn.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({condition})"))
        await conn.execute(text("CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))"))
        print("[MIGRATE] Bootstrap completed successfully.", flush=True)
    await engine.dispose()
    return True


def main() -> None:
    print("[MIGRATE] Starting database migrations check...", flush=True)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    try:
        is_empty = asyncio.run(asyncio.wait_for(_bootstrap_if_empty(), timeout=20.0))
        if is_empty:
            print("[MIGRATE] Stamping Alembic head...", flush=True)
            command.stamp(config, "head")
        else:
            print("[MIGRATE] Running Alembic upgrade to head...", flush=True)
            command.upgrade(config, "head")
        print("[MIGRATE] Database migrations completed successfully! \u2705", flush=True)
    except Exception as exc:
        print(f"\n[MIGRATE ERROR] Migration could not complete: {exc}", flush=True)
        print("[MIGRATE ERROR] Web server will proceed to start so landing page and downloads stay active.\n", flush=True)


if __name__ == "__main__":
    main()
