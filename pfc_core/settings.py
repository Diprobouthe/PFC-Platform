"""
Django settings for pfc_core project.
"""

import os
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Get SECRET_KEY from environment variable
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-pfc-platform-development-key-fallback")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG is False unless DJANGO_DEBUG environment variable is set to 'True'
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'

# ALLOWED_HOSTS configuration for Render and Sandbox
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# CSRF settings - Updated for current sandbox environment
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'https://localhost:8000',
    'http://127.0.0.1:8000',
    'https://127.0.0.1:8000',
    'http://localhost:8003',
    'https://localhost:8003',
    'http://127.0.0.1:8003',
    'https://127.0.0.1:8003',
    'http://0.0.0.0:8003',
    'https://0.0.0.0:8003',
    'https://8003-ioyu1nrpqd592r1tz64fn-6d9e8aff.manusvm.computer',
    'http://8003-ioyu1nrpqd592r1tz64fn-6d9e8aff.manusvm.computer',
]

# Add Render domain if available
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.extend([
        f"https://{RENDER_EXTERNAL_HOSTNAME}",
        f"http://{RENDER_EXTERNAL_HOSTNAME}",
    ])

# Add sandbox domain for development
sandbox_domain = os.environ.get('SANDBOX_DOMAIN')
if sandbox_domain:
    CSRF_TRUSTED_ORIGINS.extend([
        f'https://{sandbox_domain}',
        f'http://{sandbox_domain}',
    ])

# Security settings disabled for testing
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_USE_SESSIONS = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic", # Add whitenoise
    "django.contrib.staticfiles",
    # PFC Platform apps
    "tournaments",
    "matches",
    "teams",
    "leaderboards",
    "courts",
    "signin",
    "pfc_core",
    "billboard",  # Billboard module for player activity declarations
    "friendly_games",  # New parallel app for friendly games
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # Add whitenoise middleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pfc_core.urls"

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
                "pfc_core.context_processors.auth_context",
            ],
        },
    },
]

WSGI_APPLICATION = "pfc_core.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Use dj-database-url to parse the DATABASE_URL environment variable
DATABASES = {
    "default": dj_database_url.config(
        # Replace sqlite fallback with PostgreSQL if needed, but Render provides DATABASE_URL
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
# https://whitenoise.readthedocs.io/en/stable/django.html

STATIC_URL = "static/"
# Following settings only used if collecting static files
STATIC_ROOT = BASE_DIR / "staticfiles"

# Static files directories
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Enable WhiteNoise's GZip compression and forever caching
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Login URL
LOGIN_URL = "/admin/login/"


# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "matches": {  # Specific logger for the matches app
            "handlers": ["console"],
            "level": "INFO", # Use INFO for production, DEBUG if needed
            "propagate": True,
        },
        "tournaments": { # Also capture debug from tournaments if needed later
            "handlers": ["console"],
            "level": "INFO", # Use INFO for production, DEBUG if needed
            "propagate": True,
        },
    },
}

# Email settings (using console backend for development/testing)
# For production, configure a real email backend (e.g., SendGrid, Mailgun)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
ADMINS = [("Admin", "admin@example.com")] # Example admin email
