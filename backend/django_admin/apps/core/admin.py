"""Django Admin configuration for DHAN Financial Platform."""

from django.contrib import admin
from django.utils.html import format_html

from apps.core.models import (
    Account,
    AdminAuditLog,
    Asset,
    Budget,
    Category,
    DHANUser,
    Goal,
    GoalContribution,
    GroupMember,
    Liability,
    Notification,
    RecurringPayment,
    Settlement,
    SplitExpense,
    SplitGroup,
    Transaction,
)


class AuditedModelAdmin(admin.ModelAdmin):
    """Base ModelAdmin that automatically logs create, update, and delete actions into AdminAuditLog."""

    def save_model(self, request, obj, form, change):
        action = f"{'UPDATED' if change else 'CREATED'}_{obj._meta.model_name.upper()}"
        super().save_model(request, obj, form, change)
        AdminAuditLog.objects.create(
            action=action,
            performed_by=request.user.username or "admin",
            target_model=obj._meta.model_name,
            target_object_id=str(getattr(obj, "pk", "")),
            details=f"Admin {request.user.username} {'updated' if change else 'created'} {obj}",
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )

    def delete_queryset(self, request, queryset):
        """Bulk "delete selected" bypasses delete_model; log each object it removes too."""
        removed = [(str(obj.pk), str(obj)) for obj in queryset]
        super().delete_queryset(request, queryset)
        model = queryset.model._meta.model_name
        for obj_pk, obj_str in removed:
            AdminAuditLog.objects.create(
                action=f"DELETED_{model.upper()}",
                performed_by=request.user.username or "admin",
                target_model=model,
                target_object_id=obj_pk,
                details=f"Admin {request.user.username} bulk-deleted {obj_str}",
                ip_address=request.META.get("REMOTE_ADDR", ""),
            )

    def delete_model(self, request, obj):
        action = f"DELETED_{obj._meta.model_name.upper()}"
        obj_pk = str(getattr(obj, "pk", ""))
        obj_str = str(obj)
        super().delete_model(request, obj)
        AdminAuditLog.objects.create(
            action=action,
            performed_by=request.user.username or "admin",
            target_model=obj._meta.model_name,
            target_object_id=obj_pk,
            details=f"Admin {request.user.username} deleted {obj_str}",
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )


class ViewOnlyAdminMixin:
    """Admins can inspect users' financial records but not change them here.

    Editing a transaction, account or goal directly would skip the API's balance updates and
    ownership checks, leaving balances that no longer match their transactions.
    """

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def _ids(queryset) -> str:
    return ", ".join(str(pk) for pk in queryset.values_list("pk", flat=True))


@admin.register(DHANUser)
class DHANUserAdmin(AuditedModelAdmin):
    """Admin interface for managing DHAN unified users."""

    list_display = (
        "name",
        "email",
        "colored_role",
        "colored_status",
        "created_at",
        "last_login_at",
    )
    list_filter = ("role", "status")
    search_fields = ("name", "email")
    readonly_fields = (
        "id",
        "masked_password_hash",
        "created_at",
        "updated_at",
        "last_login_at",
    )
    ordering = ("-created_at",)
    actions = ["activate_users", "deactivate_users", "promote_to_admin"]

    fieldsets = (
        (
            "Account Identity",
            {
                "fields": ("id", "name", "email", "masked_password_hash"),
            },
        ),
        (
            "Permissions & Status",
            {
                "fields": ("role", "status"),
                "description": "Server-side authorization. Normal users receive role='user'; system administrators receive role='admin'.",
            },
        ),
        (
            "Audit Timestamps",
            {
                "fields": ("created_at", "updated_at", "last_login_at"),
            },
        ),
    )

    def has_add_permission(self, request):
        # Registration occurs through API or CLI; direct manual insertion restricted to prevent plain passwords
        return False

    def has_delete_permission(self, request, obj=None):
        # Deleting a user cascades through all their financial data; deactivate instead
        return False

    @admin.display(description="Role", ordering="role")
    def colored_role(self, obj):
        color = "#e11d48" if obj.role == "admin" else "#2563eb"
        badge = "👑 Admin" if obj.role == "admin" else "👤 User"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            badge,
        )

    @admin.display(description="Status", ordering="status")
    def colored_status(self, obj):
        color = "#16a34a" if obj.status == "active" else "#dc2626"
        badge = "Active" if obj.status == "active" else "Disabled"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color,
            badge,
        )

    @admin.display(description="Password Hash")
    def masked_password_hash(self, obj):
        if not obj.password_hash:
            return "None"
        # Only the scheme and cost ("$2b$12$"); no salt or hash characters are shown
        prefix = obj.password_hash[:7]
        return f"{prefix}… (bcrypt hash, never displayed)"

    @admin.action(description="Activate selected user accounts")
    def activate_users(self, request, queryset):
        ids = _ids(queryset)
        updated = queryset.update(status="active")
        self.message_user(request, f"{updated} user(s) successfully activated.")
        AdminAuditLog.objects.create(
            action="BULK_ACTIVATE_USERS",
            performed_by=request.user.username or "admin",
            target_model="DHANUser",
            details=f"Activated {updated} user account(s): {ids}",
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )

    @admin.action(description="Deactivate selected user accounts")
    def deactivate_users(self, request, queryset):
        ids = _ids(queryset)
        updated = queryset.update(status="disabled")
        self.message_user(request, f"{updated} user(s) deactivated.")
        AdminAuditLog.objects.create(
            action="BULK_DEACTIVATE_USERS",
            performed_by=request.user.username or "admin",
            target_model="DHANUser",
            details=f"Deactivated {updated} user account(s): {ids}",
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )

    @admin.action(description="Promote selected users to Administrator")
    def promote_to_admin(self, request, queryset):
        ids = _ids(queryset)
        updated = queryset.update(role="admin")
        self.message_user(request, f"{updated} user(s) promoted to Admin.")
        AdminAuditLog.objects.create(
            action="BULK_PROMOTE_ADMIN",
            performed_by=request.user.username or "admin",
            target_model="DHANUser",
            details=f"Promoted {updated} user account(s) to role='admin': {ids}",
            ip_address=request.META.get("REMOTE_ADDR", ""),
        )


@admin.register(Account)
class AccountAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = (
        "name",
        "user",
        "account_type",
        "balance",
        "currency",
        "credit_limit",
        "due_date",
        "archived",
        "is_active",
        "created_at",
    )
    list_filter = ("account_type", "currency", "archived", "is_active")
    search_fields = ("name", "institution_name", "user__name", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(Category)
class CategoryAdmin(AuditedModelAdmin):
    list_display = (
        "name",
        "category_type",
        "user",
        "ordering",
        "is_active",
        "icon",
        "color",
        "is_default",
    )
    list_filter = ("category_type", "is_default", "is_active")
    search_fields = ("name", "user__name", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("ordering", "category_type", "name")


@admin.register(Transaction)
class TransactionAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = (
        "id",
        "user",
        "amount",
        "transaction_type",
        "description",
        "account",
        "destination_account",
        "category",
        "date",
        "status",
        "is_recurring",
    )
    list_filter = ("transaction_type", "status", "is_recurring", "date")
    search_fields = ("user__name", "user__email", "description", "note")
    date_hierarchy = "date"
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-date",)


@admin.register(Budget)
class BudgetAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = (
        "user",
        "category",
        "amount",
        "month",
        "period",
        "start_date",
        "end_date",
        "warn_at_percent",
    )
    list_filter = ("period", "month", "start_date")
    search_fields = ("user__name", "category__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-start_date",)


@admin.register(SplitGroup)
class SplitGroupAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = ("name", "created_by", "currency", "created_at")
    search_fields = ("name", "created_by__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(GroupMember)
class GroupMemberAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = ("group", "user", "role", "joined_at")
    list_filter = ("role", "joined_at")
    search_fields = ("group__name", "user__name", "user__email")
    readonly_fields = ("id", "joined_at")
    ordering = ("-joined_at",)


@admin.register(SplitExpense)
class SplitExpenseAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = ("title", "group", "paid_by", "amount", "split_type", "date")
    list_filter = ("split_type", "date")
    search_fields = ("title", "paid_by__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-date",)


@admin.register(Settlement)
class SettlementAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = ("payer", "payee", "amount", "group", "status", "method", "settled_at")
    list_filter = ("status", "method")
    search_fields = ("payer__name", "payee__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)


class GoalContributionInline(ViewOnlyAdminMixin, admin.TabularInline):
    model = GoalContribution
    extra = 0
    readonly_fields = ("id", "created_at")
    fields = ("date", "amount", "account", "notes", "created_at")


@admin.register(Goal)
class GoalAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = (
        "name",
        "user",
        "icon",
        "current_amount",
        "target_amount",
        "progress_bar",
        "target_date",
        "status",
    )
    list_filter = ("status", "target_date")
    search_fields = ("name", "user__name")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [GoalContributionInline]
    ordering = ("-created_at",)

    @admin.display(description="Progress")
    def progress_bar(self, obj):
        percent = (
            min(100, int((obj.current_amount / obj.target_amount) * 100))
            if obj.target_amount > 0
            else 0
        )
        return format_html(
            '<div style="width: 100px; background-color: #e5e7eb; border-radius: 4px; overflow: hidden;">'
            '<div style="width: {}%; background-color: #3b82f6; height: 14px; text-align: center; color: white; font-size: 10px; line-height: 14px;">{}%</div>'
            "</div>",
            percent,
            percent,
        )


@admin.register(GoalContribution)
class GoalContributionAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = ("goal", "user", "amount", "date", "account", "created_at")
    list_filter = ("date", "goal")
    search_fields = ("goal__name", "user__name", "notes")
    readonly_fields = ("id", "created_at")
    ordering = ("-date", "-created_at")


@admin.register(RecurringPayment)
class RecurringPaymentAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = (
        "title",
        "user",
        "kind",
        "amount",
        "frequency",
        "next_due_date",
        "status",
        "auto_pay",
    )
    list_filter = ("kind", "frequency", "status", "auto_pay")
    search_fields = ("title", "user__name", "notes")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("next_due_date",)


@admin.register(Asset)
class AssetAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = (
        "name",
        "user",
        "asset_type",
        "current_value",
        "purchase_price",
        "purchase_date",
    )
    list_filter = ("asset_type",)
    search_fields = ("name", "user__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-current_value",)


@admin.register(Liability)
class LiabilityAdmin(ViewOnlyAdminMixin, AuditedModelAdmin):
    list_display = (
        "name",
        "user",
        "liability_type",
        "total_amount",
        "remaining_amount",
        "monthly_emi",
    )
    list_filter = ("liability_type",)
    search_fields = ("name", "user__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-remaining_amount",)


@admin.register(Notification)
class NotificationAdmin(AuditedModelAdmin):
    list_display = ("title", "user", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "user__name")
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "performed_by",
        "action",
        "target_model",
        "target_object_id",
        "ip_address",
    )
    list_filter = ("action", "target_model", "created_at")
    search_fields = ("performed_by", "action", "details")
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "action",
        "performed_by",
        "target_model",
        "target_object_id",
        "details",
        "ip_address",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        # Audit logs are generated by the system, not added manually
        return False

    def has_change_permission(self, request, obj=None):
        # Audit logs are immutable
        return False

    def has_delete_permission(self, request, obj=None):
        # Audit logs are immutable
        return False
