"""Phase 11 security tests for the Django admin."""

import os
import secrets
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
django_dir = backend_dir / "django_admin"
for path in (backend_dir, django_dir):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import django

django.setup()

from apps.core.models import Account, AdminAuditLog, DHANUser, Transaction
from django.core.cache import cache
from django.test import Client

from fastapi_app.core.security import hash_password

PASSWORD = "AdminPass123!"


def make_user(role: str = "admin", status: str = "active") -> DHANUser:
    now = datetime.now(UTC)
    return DHANUser.objects.create(
        id=uuid.uuid4(),
        name=f"{role.title()} {uuid.uuid4().hex[:4]}",
        email=f"sec_{role}_{uuid.uuid4().hex[:8]}@dhan.com",
        password_hash=hash_password(PASSWORD),
        role=role,
        status=status,
        created_at=now,
        updated_at=now,
    )


def logged_in(user: DHANUser) -> Client:
    client = Client()
    assert client.login(username=user.email, password=PASSWORD)
    return client


def test_01_demoted_or_disabled_admin_loses_access_immediately() -> None:
    """Regression: a session outlived the admin role it was granted for."""
    for change in ({"role": "user"}, {"status": "disabled"}):
        admin = make_user()
        client = logged_in(admin)
        assert client.get("/admin/").status_code == 200

        DHANUser.objects.filter(pk=admin.pk).update(**change)
        resp = client.get("/admin/")
        assert resp.status_code == 302 and "/admin/login/" in resp["Location"], change
        assert client.get("/admin/core/transaction/").status_code == 302


def test_02_normal_users_cannot_enter_the_admin() -> None:
    user = make_user(role="user")
    assert Client().login(username=user.email, password=PASSWORD) is False
    assert AdminAuditLog.objects.filter(
        action="UNAUTHORIZED_ADMIN_LOGIN_ATTEMPT", target_object_id=str(user.id)
    ).exists()


def test_03_financial_records_are_view_only() -> None:
    owner = make_user(role="user")
    account = Account.objects.create(user=owner, name="Owner Bank", balance=Decimal("1000.00"))
    tx = Transaction.objects.create(
        user=owner,
        account=account,
        amount=Decimal("250.00"),
        transaction_type="expense",
        date=datetime.now(UTC),
        status="completed",
    )
    client = logged_in(make_user())

    assert client.get(f"/admin/core/transaction/?q={owner.email}").status_code == 200
    assert client.get(f"/admin/core/transaction/{tx.pk}/change/").status_code == 200  # view
    assert client.get("/admin/core/transaction/add/").status_code == 403
    edit = client.post(
        f"/admin/core/transaction/{tx.pk}/change/", {"amount": "1.00", "note": "tampered"}
    )
    assert edit.status_code == 403
    assert (
        client.post(f"/admin/core/transaction/{tx.pk}/delete/", {"post": "yes"}).status_code == 403
    )
    assert (
        client.post(f"/admin/core/account/{account.pk}/change/", {"balance": "999999"}).status_code
        == 403
    )

    tx.refresh_from_db()
    account.refresh_from_db()
    assert tx.amount == Decimal("250.00") and account.balance == Decimal("1000.00")


def test_04_users_can_be_managed_but_not_deleted() -> None:
    client = logged_in(make_user())
    target = make_user(role="user")
    assert (
        client.post(f"/admin/core/dhanuser/{target.pk}/delete/", {"post": "yes"}).status_code == 403
    )
    assert DHANUser.objects.filter(pk=target.pk).exists()

    resp = client.post(
        "/admin/core/dhanuser/",
        {"action": "deactivate_users", "_selected_action": [str(target.pk)]},
    )
    assert resp.status_code == 302
    target.refresh_from_db()
    assert target.status == "disabled"
    log = (
        AdminAuditLog.objects.filter(action="BULK_DEACTIVATE_USERS").order_by("-created_at").first()
    )
    assert log is not None and str(target.pk) in log.details  # who was affected is recorded


def test_05_audit_log_is_immutable() -> None:
    client = logged_in(make_user())
    entry = AdminAuditLog.objects.create(action="TEST_ENTRY", performed_by="test")
    assert (
        client.post(
            f"/admin/core/adminauditlog/{entry.pk}/change/", {"action": "ERASED"}
        ).status_code
        == 403
    )
    assert (
        client.post(f"/admin/core/adminauditlog/{entry.pk}/delete/", {"post": "yes"}).status_code
        == 403
    )
    assert client.get("/admin/core/adminauditlog/add/").status_code == 403
    entry.refresh_from_db()
    assert entry.action == "TEST_ENTRY"


def test_06_admin_password_guessing_is_throttled() -> None:
    cache.clear()
    admin = make_user()
    for _ in range(5):
        assert Client().login(username=admin.email, password="wrong-guess") is False
    # Now even the right password is refused until the cool-off ends
    assert Client().login(username=admin.email, password=PASSWORD) is False
    assert AdminAuditLog.objects.filter(
        action="ADMIN_LOGIN_THROTTLED", performed_by=admin.email
    ).exists()
    cache.clear()
    assert Client().login(username=admin.email, password=PASSWORD) is True


def test_07_password_hash_is_not_displayed() -> None:
    client = logged_in(make_user())
    target = make_user(role="user")
    page = client.get(f"/admin/core/dhanuser/{target.pk}/change/").content.decode()
    assert target.password_hash[:7] in page  # "$2b$12$": scheme and cost only
    assert target.password_hash[7:20] not in page


def _deploy_check(env_overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **env_overrides}
    env.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
    return subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=django_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_08_production_settings_are_enforced() -> None:
    unsafe = _deploy_check(
        {
            "ENVIRONMENT": "production",
            "DJANGO_DEBUG": "True",
            "DJANGO_SECRET_KEY": "dhan-django-insecure-secret-key-change-in-production-abcdef",
            "DJANGO_ALLOWED_HOSTS": "*",
        }
    )
    assert unsafe.returncode != 0
    assert "Refusing to start in production" in unsafe.stderr

    safe = _deploy_check(
        {
            "ENVIRONMENT": "production",
            "DJANGO_DEBUG": "False",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
            "DJANGO_ALLOWED_HOSTS": "admin.dhan.example",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://admin.dhan.example",
            "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
        }
    )
    assert safe.returncode == 0, safe.stdout + safe.stderr
    assert "no issues" in safe.stdout
