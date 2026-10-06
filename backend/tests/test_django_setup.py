"""Test Django Admin configuration and setup."""

import os
import sys
from pathlib import Path

# Setup Django environment
django_dir = Path(__file__).resolve().parent.parent / "django_admin"
if str(django_dir) not in sys.path:
    sys.path.insert(0, str(django_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from apps.core.models import AdminAuditLog
from django.apps import apps
from django.conf import settings


def test_django_apps_loaded() -> None:
    """Verify that Django core apps and admin are configured."""
    assert apps.is_installed("django.contrib.admin")
    assert apps.is_installed("apps.core")


def test_django_database_configuration() -> None:
    """Verify that Django default database is configured for PostgreSQL."""
    default_db = settings.DATABASES["default"]
    assert default_db["ENGINE"] == "django.db.backends.postgresql"
    assert default_db["NAME"] == os.environ.get("POSTGRES_DB", "dhan_db")


def test_admin_model_definition() -> None:
    """Verify AdminAuditLog model fields and table name."""
    assert AdminAuditLog._meta.db_table == "django_admin_audit_logs"
    fields = [f.name for f in AdminAuditLog._meta.get_fields()]
    assert "action" in fields
    assert "performed_by" in fields
    assert "created_at" in fields
