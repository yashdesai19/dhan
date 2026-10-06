"""Django models for DHAN Financial Platform Core Administration."""

import uuid

from django.db import models
from django.utils import timezone


class DHANUser(models.Model):
    """Unmanaged Django representation of the shared PostgreSQL 'users' table."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20,
        choices=[("user", "Normal User"), ("admin", "Administrator")],
        default="user",
    )
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("disabled", "Disabled")],
        default="active",
    )
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "users"
        managed = False
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.email}) [{self.role}]"

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_active_user(self) -> bool:
        return self.status == "active"


class AdminAuditLog(models.Model):
    """Tracks administrative and sensitive operations executed via Django Admin."""

    action = models.CharField(max_length=255)
    performed_by = models.CharField(max_length=150, default="system")
    target_model = models.CharField(max_length=100, blank=True, default="")
    target_object_id = models.CharField(max_length=100, blank=True, default="")
    details = models.TextField(blank=True, default="")
    ip_address = models.CharField(max_length=45, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "django_admin_audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        timestamp = f"{self.created_at:%Y-%m-%d %H:%M}" if self.created_at else "Pending"
        return f"[{timestamp}] {self.performed_by}: {self.action} ({self.target_model})"


class Account(models.Model):
    """Financial accounts owned by users (Bank, Cash, Investment, Wallet, etc.)."""

    ACCOUNT_TYPES = [
        ("bank", "Bank Account"),
        ("cash", "Physical Cash"),
        ("credit_card", "Credit Card"),
        ("investment", "Investment / Demat"),
        ("wallet", "Digital Wallet"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="accounts",
        db_column="user_id",
    )
    name = models.CharField(max_length=100, help_text="e.g. HDFC Salary Account, Cash Wallet")
    account_type = models.CharField(max_length=30, choices=ACCOUNT_TYPES, default="bank")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default="INR")
    institution_name = models.CharField(
        max_length=100, blank=True, help_text="e.g. HDFC, ICICI, SBI"
    )
    account_number_mask = models.CharField(max_length=20, blank=True, help_text="e.g. •••• 4321")
    is_active = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)
    include_in_total = models.BooleanField(
        default=True, help_text="Counted in net balance and net worth"
    )
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    due_date = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_accounts"
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_account_type_display()}) - {self.currency} {self.balance}"


class Category(models.Model):
    """Expense, Income, and Transfer categories for transaction categorization."""

    CATEGORY_TYPES = [
        ("expense", "Expense"),
        ("income", "Income"),
        ("transfer", "Transfer"),
        ("split", "Group expense payment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="categories",
        db_column="user_id",
    )
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default="expense")
    icon = models.CharField(max_length=50, blank=True, help_text="Material or Ionic icon name")
    color = models.CharField(max_length=20, blank=True, help_text="Hex color code e.g. #FF5733")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subcategories",
    )
    is_default = models.BooleanField(default=True, help_text="Default platform category")
    is_active = models.BooleanField(default=True)
    ordering = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_categories"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["ordering", "category_type", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_type_display()})"


class Transaction(models.Model):
    """Core financial ledger transactions recorded by users."""

    TRANSACTION_TYPES = [
        ("expense", "Expense"),
        ("income", "Income"),
        ("transfer", "Transfer"),
    ]

    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("pending", "Pending"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="transactions",
        db_column="user_id",
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    destination_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transfers_received",
        db_column="destination_account_id",
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255, blank=True, default="")
    date = models.DateTimeField(help_text="Transaction execution timestamp")
    note = models.TextField(blank=True, help_text="User transaction description")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_transactions"
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.user.name}: {self.transaction_type.upper()} {self.amount} on {self.date:%Y-%m-%d}"


class Budget(models.Model):
    """Budget ceilings allocated per category over a specific period."""

    PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("weekly", "Weekly"),
        ("yearly", "Yearly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="budgets",
        db_column="user_id",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="budgets",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default="monthly")
    month = models.CharField(max_length=7, blank=True, null=True, help_text="e.g. 2026-09")
    start_date = models.DateField()
    end_date = models.DateField()
    warn_at_percent = models.IntegerField(default=90)
    rollover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_budgets"
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        ordering = ["-start_date"]

    def __str__(self) -> str:
        cat_name = self.category.name if self.category else "Overall"
        return f"{self.user.name}: {cat_name} Budget ({self.amount} / {self.period})"


class SplitGroup(models.Model):
    """Collaborative expense splitting groups (e.g. Trips, Roommates, Project team)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="created_groups",
        db_column="created_by_id",
    )
    currency = models.CharField(max_length=3, default="INR")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_groups"
        verbose_name = "Group"
        verbose_name_plural = "Groups"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Group: {self.name} (by {self.created_by.name})"


class GroupMember(models.Model):
    """Membership record linking a User to a SplitGroup."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        SplitGroup,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="group_memberships",
        db_column="user_id",
    )
    role = models.CharField(max_length=20, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dhan_group_members"
        verbose_name = "Group Member"
        verbose_name_plural = "Group Members"
        unique_together = ("group", "user")

    def __str__(self) -> str:
        return f"{self.user.name} in {self.group.name} ({self.role})"


class SplitExpense(models.Model):
    """Shared expense split within a group or between individuals."""

    SPLIT_TYPES = [
        ("equal", "Equal Split"),
        ("exact", "Exact Amounts"),
        ("percentage", "Percentage"),
        ("shares", "Shares"),
        ("itemwise", "Item-wise"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        SplitGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="splits",
    )
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_by = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="paid_splits",
        db_column="paid_by_id",
    )
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPES, default="equal")
    shares = models.JSONField(default=dict, blank=True)
    split_details = models.JSONField(null=True, blank=True)
    date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_splits"
        verbose_name = "Split"
        verbose_name_plural = "Splits"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.title}: {self.amount} (Paid by {self.paid_by.name})"


class Settlement(models.Model):
    """Settlement payment resolving split balances between group members."""

    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("pending", "Pending Verification"),
        ("cancelled", "Cancelled"),
    ]

    METHOD_CHOICES = [
        ("upi", "UPI"),
        ("cash", "Cash"),
        ("bank", "Bank Transfer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        SplitGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="settlements",
    )
    payer = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="settlements_paid",
        db_column="payer_id",
    )
    payee = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="settlements_received",
        db_column="payee_id",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="upi")
    notes = models.TextField(blank=True, null=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_settlements"
        verbose_name = "Settlement"
        verbose_name_plural = "Settlements"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Settlement: {self.payer.name} -> {self.payee.name}: {self.amount} [{self.status}]"


class Goal(models.Model):
    """Financial savings targets set by users."""

    STATUS_CHOICES = [
        ("in_progress", "In Progress"),
        ("achieved", "Achieved"),
        ("paused", "Paused"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="goals",
        db_column="user_id",
    )
    name = models.CharField(max_length=150, help_text="e.g. Emergency Fund, New Bike, Vacation")
    icon = models.CharField(max_length=50, default="target")
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    target_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_goals"
        verbose_name = "Goal"
        verbose_name_plural = "Goals"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        percent = (self.current_amount / self.target_amount * 100) if self.target_amount > 0 else 0
        return f"{self.user.name}: {self.name} ({percent:.1f}% of {self.target_amount})"


class GoalContribution(models.Model):
    """Individual financial contributions toward reaching a specific goal."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="contributions",
        db_column="goal_id",
    )
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="goal_contributions",
        db_column="user_id",
    )
    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="goal_contributions",
        db_column="account_id",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dhan_goal_contributions"
        verbose_name = "Goal Contribution"
        verbose_name_plural = "Goal Contributions"
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return f"Contribution: {self.amount} to {self.goal.name} on {self.date}"


class RecurringPayment(models.Model):
    """Subscriptions, EMIs, and scheduled recurring utility bills."""

    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("paused", "Paused"),
        ("cancelled", "Cancelled"),
    ]

    KIND_CHOICES = [
        ("bill", "Bill"),
        ("emi", "EMI"),
        ("subscription", "Subscription"),
        ("income", "Recurring Income"),
        ("expense", "Recurring Expense"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="recurring_payments",
        db_column="user_id",
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=150, help_text="e.g. Netflix Subscription, House Rent, Gym")
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default="bill")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="monthly")
    next_due_date = models.DateField()
    anchor_day = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Day of month the schedule is pinned to (1-31)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    auto_pay = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    metadata_json = models.JSONField(null=True, blank=True)
    last_paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_recurring_payments"
        verbose_name = "Recurring Payment"
        verbose_name_plural = "Recurring Payments"
        ordering = ["next_due_date"]

    def __str__(self) -> str:
        return f"{self.title}: {self.amount} ({self.get_frequency_display()}) - Due: {self.next_due_date}"


class Asset(models.Model):
    """Net worth assets: Real Estate, Stocks, Mutual Funds, Gold, Crypto, Fixed Deposits."""

    ASSET_TYPES = [
        ("stock", "Stocks"),
        ("mutual_fund", "Mutual Funds"),
        ("epf", "Provident Fund (EPF/PPF)"),
        ("crypto", "Cryptocurrency"),
        ("real_estate", "Real Estate"),
        ("gold", "Precious Metals / Gold"),
        ("fixed_deposit", "Fixed Deposit"),
        ("cash", "Cash & Equivalents"),
        ("other", "Other Asset"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="assets",
        db_column="user_id",
    )
    name = models.CharField(max_length=150, help_text="e.g. Nifty 50 Index, Sovereign Gold Bond")
    asset_type = models.CharField(max_length=30, choices=ASSET_TYPES)
    current_value = models.DecimalField(max_digits=15, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_assets"
        verbose_name = "Asset"
        verbose_name_plural = "Assets"
        ordering = ["-current_value"]

    def __str__(self) -> str:
        return f"{self.user.name}: {self.name} [{self.get_asset_type_display()}] - {self.current_value}"


class Liability(models.Model):
    """Net worth liabilities: Mortgages, Auto Loans, Personal Loans, Credit Card Debts."""

    LIABILITY_TYPES = [
        ("mortgage", "Home Loan / Mortgage"),
        ("auto_loan", "Vehicle Loan"),
        ("personal_loan", "Personal Loan"),
        ("credit_card", "Credit Card Outstanding"),
        ("student_loan", "Education Loan"),
        ("other", "Other Debt"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="liabilities",
        db_column="user_id",
    )
    name = models.CharField(max_length=150, help_text="e.g. SBI Home Loan, Car Loan")
    liability_type = models.CharField(max_length=30, choices=LIABILITY_TYPES)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    monthly_emi = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dhan_liabilities"
        verbose_name = "Liability"
        verbose_name_plural = "Liabilities"
        ordering = ["-remaining_amount"]

    def __str__(self) -> str:
        return f"{self.user.name}: {self.name} [{self.get_liability_type_display()}] - Remaining: {self.remaining_amount}"


class Notification(models.Model):
    """User notifications and administrative announcements."""

    NOTIFICATION_TYPES = [
        ("alert", "Security Alert"),
        ("reminder", "Bill Reminder"),
        ("budget", "Budget Exceeded Warning"),
        ("system", "System Update"),
        ("transaction", "Transaction Confirmation"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        DHANUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_column="user_id",
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30, choices=NOTIFICATION_TYPES, default="system"
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dhan_notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        read_flag = "Read" if self.is_read else "Unread"
        return f"[{read_flag}] {self.user.name}: {self.title}"
