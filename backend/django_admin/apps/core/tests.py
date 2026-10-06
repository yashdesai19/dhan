"""Django native unit and integration tests for DHAN Admin."""

import uuid
from decimal import Decimal

from django.contrib import admin
from django.test import TestCase

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


class DHANAdminModelRegistryTests(TestCase):
    """Test that all 14 core financial models are registered with the Django admin site."""

    def test_all_models_registered(self):
        registered = admin.site._registry
        models = [
            DHANUser,
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
            AdminAuditLog,
        ]
        for m in models:
            self.assertIn(m, registered, f"{m.__name__} not in admin registry")


class DHANAdminModelCreationTests(TestCase):
    """Test model creation and string representations."""

    def setUp(self):
        # Create user directly using DHANUser
        self.user_id = uuid.uuid4()
        self.user = DHANUser(
            id=self.user_id,
            name="Test User",
            email="test@dhan.com",
            role="user",
            status="active",
        )

    def test_account_creation(self):
        acc = Account(
            id=uuid.uuid4(),
            user=self.user,
            name="Savings Account",
            account_type="bank",
            balance=Decimal("1000.00"),
            currency="INR",
        )
        self.assertIn("Savings Account", str(acc))

    def test_category_creation(self):
        cat = Category(
            id=uuid.uuid4(),
            name="Groceries",
            category_type="expense",
        )
        self.assertIn("Groceries", str(cat))

    def test_goal_creation(self):
        goal = Goal(
            id=uuid.uuid4(),
            user=self.user,
            name="New Laptop",
            target_amount=Decimal("80000.00"),
            current_amount=Decimal("40000.00"),
            target_date="2026-12-31",
            status="in_progress",
        )
        self.assertIn("50.0%", str(goal))

    def test_audit_log_creation(self):
        log = AdminAuditLog(
            action="TEST_ACTION",
            performed_by="admin@dhan.com",
            target_model="DHANUser",
            details="Unit test audit log",
        )
        self.assertIn("TEST_ACTION", str(log))
