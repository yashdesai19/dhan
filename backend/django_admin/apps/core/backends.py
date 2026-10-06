"""Custom authentication backend allowing DHAN administrators to log into Django Admin."""

import logging

import bcrypt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.core.cache import cache

from apps.core.models import AdminAuditLog, DHANUser

logger = logging.getLogger(__name__)
DjangoUser = get_user_model()

# Checked when no DHAN user matches, so unknown emails take as long as wrong passwords
_TIMING_DUMMY_HASH = bcrypt.hashpw(b"dhan-admin-timing-equaliser", bcrypt.gensalt(rounds=12))


def _failure_key(email: str) -> str:
    return f"dhan-admin-login-failures:{email}"


def _record_failure(email: str) -> None:
    key = _failure_key(email)
    cache.add(key, 0, timeout=settings.ADMIN_LOGIN_LOCKOUT_SECONDS)
    try:
        cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, timeout=settings.ADMIN_LOGIN_LOCKOUT_SECONDS)


def is_active_dhan_admin(email: str) -> bool:
    """Whether the DHAN account behind an admin session may still use the admin."""
    return DHANUser.objects.filter(email__iexact=email, role="admin", status="active").exists()


class DHANAdminAuthBackend(BaseBackend):
    """Authenticate authorized DHAN administrators from the shared 'users' database table."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        clean_username = username.strip().lower()

        # 0. Cool-off after repeated failures, whatever the password this time
        if cache.get(_failure_key(clean_username), 0) >= settings.ADMIN_LOGIN_MAX_FAILURES:
            logger.warning("Admin login throttled after repeated failures")
            AdminAuditLog.objects.create(
                action="ADMIN_LOGIN_THROTTLED",
                performed_by=clean_username,
                target_model="DHANUser",
                details="Too many failed admin logins; attempt refused without checking.",
            )
            return None

        try:
            # 1. Look up user in the shared DHAN users table
            dhan_user = DHANUser.objects.filter(email__iexact=clean_username).first()
            if not dhan_user:
                bcrypt.checkpw(password.encode("utf-8")[:72], _TIMING_DUMMY_HASH)
                _record_failure(clean_username)
                return None

            # 2. Check password with bcrypt
            try:
                is_valid = bcrypt.checkpw(
                    password.encode("utf-8"),
                    dhan_user.password_hash.encode("utf-8"),
                )
            except Exception as exc:
                logger.warning(f"Error checking password hash for {clean_username}: {exc}")
                return None

            if not is_valid:
                _record_failure(clean_username)
                return None

            # 3. CRITICAL SECURITY RULE: Only users with role='admin' may enter Django Admin
            if dhan_user.role != "admin":
                logger.warning(
                    f"Access denied for non-admin user {clean_username} attempting Django Admin login."
                )
                # Audit unauthorized attempt
                AdminAuditLog.objects.create(
                    action="UNAUTHORIZED_ADMIN_LOGIN_ATTEMPT",
                    performed_by=clean_username,
                    target_model="DHANUser",
                    target_object_id=str(dhan_user.id),
                    details=f"User with role '{dhan_user.role}' attempted Django Admin access.",
                )
                return None

            # 4. Check if account is active
            if dhan_user.status != "active":
                logger.warning(f"Access denied for disabled admin user {clean_username}.")
                return None

            # 5. Sync or get Django internal auth user for session management
            django_user, created = DjangoUser.objects.get_or_create(
                username=dhan_user.email,
                defaults={
                    "email": dhan_user.email,
                    "first_name": dhan_user.name,
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                },
            )

            # Ensure admin permissions remain active
            if not django_user.is_staff or not django_user.is_superuser:
                django_user.is_staff = True
                django_user.is_superuser = True
                django_user.is_active = True
                django_user.save()

            # Record successful admin login in audit log
            AdminAuditLog.objects.create(
                action="ADMIN_LOGIN_SUCCESS",
                performed_by=clean_username,
                target_model="DHANUser",
                target_object_id=str(dhan_user.id),
                details=f"Admin {dhan_user.name} ({clean_username}) logged into Django Admin.",
            )

            return django_user

        except Exception as exc:
            logger.error(f"Unexpected error in DHANAdminAuthBackend: {exc}")
            return None

    def get_user(self, user_id):
        """Runs on every admin request: the session only stays valid while the DHAN account
        is still an active admin, so demoting or disabling someone ends their admin access
        immediately rather than when the session cookie expires."""
        try:
            django_user = DjangoUser.objects.get(pk=user_id)
        except DjangoUser.DoesNotExist:
            return None
        if not is_active_dhan_admin(django_user.username):
            logger.warning("Admin session ended: account is no longer an active admin")
            return None
        return django_user
