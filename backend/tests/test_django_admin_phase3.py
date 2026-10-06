"""Comprehensive test suite for Phase 3: Django Admin features, models, authorization, and audit logs."""

import os
import sys
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

# Ensure django_admin is on sys.path
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

from apps.core.models import (
    Account,
    AdminAuditLog,
    Asset,
    Budget,
    Category,
    DHANUser,
    Goal,
    Liability,
    Notification,
    RecurringPayment,
    Settlement,
    SplitExpense,
    SplitGroup,
    Transaction,
)
from django.contrib import admin
from django.core.management import call_command
from django.test import Client

from fastapi_app.core.security import hash_password


def test_01_django_system_check() -> None:
    """1. Test Django system check passes without warnings or errors."""
    call_command("check")


def test_02_all_14_models_registered_in_admin() -> None:
    """Verify that all 14 required financial and infrastructure models are registered in Django admin."""
    required_models = [
        DHANUser,
        AdminAuditLog,
        Account,
        Category,
        Transaction,
        Budget,
        SplitGroup,
        SplitExpense,
        Settlement,
        Goal,
        RecurringPayment,
        Asset,
        Liability,
        Notification,
    ]
    registered_models = list(admin.site._registry.keys())
    for model in required_models:
        assert model in registered_models, (
            f"Model {model.__name__} is NOT registered in Django Admin!"
        )


def test_03_admin_login_and_access_with_dhan_admin_user() -> None:
    """4. Test that a DHAN user with role='admin' can log into Django Admin."""
    admin_email = f"admin_phase3_{uuid.uuid4().hex[:6]}@dhan.com"
    raw_pwd = "AdminSecurePass123!"

    # Create admin in shared DHAN database
    now = datetime.now(UTC)
    DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Chief Admin",
        email=admin_email,
        password_hash=hash_password(raw_pwd),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    client = Client()
    login_success = client.login(username=admin_email, password=raw_pwd)
    assert login_success is True, "Admin authentication via DHANAdminAuthBackend failed!"

    # Admin visits admin index
    resp = client.get("/admin/")
    assert resp.status_code == 200
    assert "DHAN Financial Platform Administration" in resp.content.decode("utf-8")


def test_04_normal_user_denied_admin_access() -> None:
    """14. Test that a normal DHAN user (role='user') is REJECTED from Django Admin."""
    normal_email = f"normal_phase3_{uuid.uuid4().hex[:6]}@dhan.com"
    raw_pwd = "NormalUserPass123!"

    now = datetime.now(UTC)
    DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Regular Investor",
        email=normal_email,
        password_hash=hash_password(raw_pwd),
        role="user",  # Normal user
        status="active",
        created_at=now,
        updated_at=now,
    )

    client = Client()
    login_success = client.login(username=normal_email, password=raw_pwd)
    assert login_success is False, (
        "Normal user MUST NOT be allowed to authenticate into Django Admin!"
    )

    # Attempt direct get on admin dashboard
    resp = client.get("/admin/")
    # Unauthenticated client is redirected to login (302)
    assert resp.status_code == 302


def test_05_admin_can_see_and_search_users() -> None:
    """5 & 6. Test that authorized admin can view and search DHAN users."""
    search_token = f"SpecialSearch_{uuid.uuid4().hex[:4]}"
    search_email = f"{search_token.lower()}@dhan.com"
    now = datetime.now(UTC)

    # Setup admin
    admin_email = f"admin_search_{uuid.uuid4().hex[:6]}@dhan.com"
    DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Search Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    # Setup target user to find
    DHANUser.objects.create(
        id=uuid.uuid4(),
        name=search_token,
        email=search_email,
        password_hash=hash_password("Pass12345!"),
        role="user",
        status="active",
        created_at=now,
        updated_at=now,
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    # 1. View user changelist
    resp = client.get("/admin/core/dhanuser/")
    assert resp.status_code == 200

    # 2. Search by name query param
    resp_search = client.get(f"/admin/core/dhanuser/?q={search_token}")
    assert resp_search.status_code == 200
    html = resp_search.content.decode("utf-8")
    assert search_token in html
    assert search_email in html


def test_06_admin_can_filter_users() -> None:
    """7. Test that admin can filter users by role and status."""
    admin_email = f"admin_filter_{uuid.uuid4().hex[:6]}@dhan.com"
    now = datetime.now(UTC)
    DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Filter Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    # Filter by role=admin
    resp_role = client.get("/admin/core/dhanuser/?role=admin")
    assert resp_role.status_code == 200

    # Filter by status=active
    resp_status = client.get("/admin/core/dhanuser/?status=active")
    assert resp_status.status_code == 200


def test_07_admin_can_view_accounts() -> None:
    """8. Test that admin can view financial accounts."""
    now = datetime.now(UTC)
    admin_email = f"admin_acc_{uuid.uuid4().hex[:6]}@dhan.com"
    admin_u = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Account Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    Account.objects.create(
        user=admin_u,
        name="HDFC Wealth Savings",
        account_type="bank",
        balance=Decimal("250000.50"),
        currency="INR",
        institution_name="HDFC Bank",
        account_number_mask="•••• 8899",
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    resp = client.get("/admin/core/account/")
    assert resp.status_code == 200
    assert "HDFC Wealth Savings" in resp.content.decode("utf-8")


def test_08_admin_can_view_transactions() -> None:
    """9. Test that admin can view transactions and categories."""
    now = datetime.now(UTC)
    admin_email = f"admin_tx_{uuid.uuid4().hex[:6]}@dhan.com"
    admin_u = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Tx Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    acc = Account.objects.create(user=admin_u, name="Main Checking", balance=Decimal("50000.00"))
    cat = Category.objects.create(name="Groceries & Food", category_type="expense")

    Transaction.objects.create(
        user=admin_u,
        account=acc,
        category=cat,
        amount=Decimal("3450.75"),
        transaction_type="expense",
        date=now,
        note="Weekly Supermarket Restock",
        status="completed",
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    # Search by this admin's email: the shared test database keeps every run's rows, so a
    # fresh record isn't guaranteed to be on the first page of the full list
    resp = client.get("/admin/core/transaction/", {"q": admin_email})
    assert resp.status_code == 200
    assert "3450.75" in resp.content.decode("utf-8")


def test_09_admin_can_view_budgets() -> None:
    """10. Test that admin can view budgets."""
    now = datetime.now(UTC)
    admin_email = f"admin_bg_{uuid.uuid4().hex[:6]}@dhan.com"
    admin_u = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Budget Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    cat = Category.objects.create(name="Entertainment", category_type="expense")
    Budget.objects.create(
        user=admin_u,
        category=cat,
        amount=Decimal("15000.00"),
        period="monthly",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    resp = client.get("/admin/core/budget/")
    assert resp.status_code == 200
    assert "Entertainment" in resp.content.decode("utf-8")


def test_10_admin_can_view_splits_and_settlements() -> None:
    """11. Test that admin can view groups, splits, and settlements."""
    now = datetime.now(UTC)
    admin_email = f"admin_split_{uuid.uuid4().hex[:6]}@dhan.com"
    admin_u = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Split Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    friend = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Rohan Sharma",
        email=f"rohan_{uuid.uuid4().hex[:6]}@dhan.com",
        password_hash=hash_password("Pass12345!"),
        role="user",
        status="active",
        created_at=now,
        updated_at=now,
    )

    group = SplitGroup.objects.create(name="Manali Expedition", created_by=admin_u)
    SplitExpense.objects.create(
        group=group,
        title="Resort Booking",
        amount=Decimal("18000.00"),
        paid_by=admin_u,
        date=now,
    )
    Settlement.objects.create(
        group=group,
        payer=friend,
        payee=admin_u,
        amount=Decimal("9000.00"),
        status="completed",
        settled_at=now,
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    resp_split = client.get("/admin/core/splitexpense/")
    assert resp_split.status_code == 200
    assert "Resort Booking" in resp_split.content.decode("utf-8")

    resp_settle = client.get("/admin/core/settlement/")
    assert resp_settle.status_code == 200
    assert "9000.00" in resp_settle.content.decode("utf-8")


def test_11_admin_can_view_goals() -> None:
    """12. Test that admin can view savings goals."""
    now = datetime.now(UTC)
    admin_email = f"admin_goal_{uuid.uuid4().hex[:6]}@dhan.com"
    admin_u = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Goal Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    Goal.objects.create(
        user=admin_u,
        name="Emergency Corpus 2026",
        target_amount=Decimal("500000.00"),
        current_amount=Decimal("250000.00"),
        target_date=date(2026, 12, 31),
        status="in_progress",
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    resp = client.get("/admin/core/goal/")
    assert resp.status_code == 200
    assert "Emergency Corpus 2026" in resp.content.decode("utf-8")


def test_12_admin_can_view_recurring_payments() -> None:
    """13. Test that admin can view recurring payments."""
    now = datetime.now(UTC)
    admin_email = f"admin_rec_{uuid.uuid4().hex[:6]}@dhan.com"
    admin_u = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Recurring Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    acc = Account.objects.create(user=admin_u, name="Bill Pay Account", balance=Decimal("10000.00"))
    RecurringPayment.objects.create(
        user=admin_u,
        account=acc,
        title="AWS Cloud Hosting",
        amount=Decimal("4200.00"),
        frequency="monthly",
        next_due_date=date(2026, 10, 15),
        status="active",
        auto_pay=True,
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    # Filter to this admin's rows: earlier runs' payments can fill the first page
    resp = client.get("/admin/core/recurringpayment/", {"user__id__exact": str(admin_u.id)})
    assert resp.status_code == 200
    assert "AWS Cloud Hosting" in resp.content.decode("utf-8")


def test_13_admin_can_view_assets_liabilities_notifications() -> None:
    """Test that admin can view Assets, Liabilities, and Notifications."""
    now = datetime.now(UTC)
    admin_email = f"admin_wealth_{uuid.uuid4().hex[:6]}@dhan.com"
    admin_u = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Wealth Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    Asset.objects.create(
        user=admin_u,
        name="Nifty BeES ETF",
        asset_type="stock",
        current_value=Decimal("750000.00"),
    )
    Liability.objects.create(
        user=admin_u,
        name="Car Loan HDFC",
        liability_type="auto_loan",
        total_amount=Decimal("800000.00"),
        remaining_amount=Decimal("350000.00"),
    )
    Notification.objects.create(
        user=admin_u,
        title="Dividend Credit Alert",
        message="INR 1250 received from Nifty BeES.",
        notification_type="transaction",
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    resp_a = client.get("/admin/core/asset/")
    assert resp_a.status_code == 200
    assert "Nifty BeES ETF" in resp_a.content.decode("utf-8")

    resp_l = client.get("/admin/core/liability/")
    assert resp_l.status_code == 200
    assert "Car Loan HDFC" in resp_l.content.decode("utf-8")

    resp_n = client.get("/admin/core/notification/")
    assert resp_n.status_code == 200
    assert "Dividend Credit Alert" in resp_n.content.decode("utf-8")


def test_14_user_deactivation_action_and_audit_logging() -> None:
    """15. Test user deactivation action and verify audit log generation."""
    now = datetime.now(UTC)
    admin_email = f"admin_audit_{uuid.uuid4().hex[:6]}@dhan.com"
    DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Auditor Admin",
        email=admin_email,
        password_hash=hash_password("Pass12345!"),
        role="admin",
        status="active",
        created_at=now,
        updated_at=now,
    )

    victim = DHANUser.objects.create(
        id=uuid.uuid4(),
        name="Fraudulent Account",
        email=f"fraud_{uuid.uuid4().hex[:6]}@dhan.com",
        password_hash=hash_password("Pass12345!"),
        role="user",
        status="active",
        created_at=now,
        updated_at=now,
    )

    client = Client()
    client.login(username=admin_email, password="Pass12345!")

    # Post admin action to deactivate user
    resp_action = client.post(
        "/admin/core/dhanuser/",
        {
            "action": "deactivate_users",
            admin.helpers.ACTION_CHECKBOX_NAME: [str(victim.id)],
        },
    )
    assert resp_action.status_code in [200, 302]

    # Verify status changed in database
    victim.refresh_from_db()
    assert victim.status == "disabled"

    # Verify audit log was recorded
    audit_entry = AdminAuditLog.objects.filter(action="BULK_DEACTIVATE_USERS").first()
    assert audit_entry is not None
    assert audit_entry.performed_by == admin_email
    assert "Deactivated 1 user" in audit_entry.details
