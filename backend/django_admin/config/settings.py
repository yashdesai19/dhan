"""Django settings for DHAN Admin project."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR.parent

# Load environment variables from backend/.env if available
env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").strip().lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod", "staging")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dhan-django-insecure-secret-key-change-in-production-abcdef",
)

# Off unless asked for: debug pages expose settings and stack traces
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if host.strip()
]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Internal apps
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database Configuration: Shared PostgreSQL database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "dhan_db"),
        "USER": os.environ.get("POSTGRES_USER", "dhan_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "dhan_password"),
        "HOST": os.environ.get("POSTGRES_SERVER", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication backends: DHAN shared database admin backend first, then standard fallback
AUTHENTICATION_BACKENDS = [
    "apps.core.backends.DHANAdminAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# --------------------------------------------------------------------------
# Security hardening
# --------------------------------------------------------------------------

# Admin sessions: short-lived, cookie unreadable by scripts, not sent cross-site
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Failed DHAN admin logins allowed per account before a cool-off (see apps.core.backends)
ADMIN_LOGIN_MAX_FAILURES = 5
ADMIN_LOGIN_LOCKOUT_SECONDS = 15 * 60

if IS_PRODUCTION:
    # Served over HTTPS behind a TLS-terminating proxy
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "True").lower() in (
        "true",
        "1",
        "yes",
    )
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # HSTS preload is a long-lived promise for the whole domain, made by its owner when ready:
    # opt in with DJANGO_HSTS_PRELOAD=true (the deploy check reminds about it otherwise).
    SECURE_HSTS_PRELOAD = os.environ.get("DJANGO_HSTS_PRELOAD", "False").lower() in ("true", "1")
    if not SECURE_HSTS_PRELOAD:
        SILENCED_SYSTEM_CHECKS = ["security.W021"]
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
        if origin.strip()
    ]

    _problems = []
    if DEBUG:
        _problems.append("DJANGO_DEBUG must be false")
    if "insecure" in SECRET_KEY or len(SECRET_KEY) < 50:
        _problems.append("DJANGO_SECRET_KEY must be a unique random value of 50+ characters")
    if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
        _problems.append("DJANGO_ALLOWED_HOSTS must list the admin's host names, not '*'")
    if DATABASES["default"]["PASSWORD"] == "dhan_password":
        _problems.append("POSTGRES_PASSWORD must not be the development password")
    if _problems:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured("Refusing to start in production: " + "; ".join(_problems))
