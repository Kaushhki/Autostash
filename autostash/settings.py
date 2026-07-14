"""
Django settings for the AutoStash project.

AutoStash — Automated Debt Payoff Optimization Engine.

All the values that differ between local dev and a real deployment are
read from environment variables, with dev-friendly defaults so nothing
extra is needed to just `runserver` locally.
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# In production, set a real SECRET_KEY env var (e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production-CHANGE-ME')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Comma-separated in production, e.g. "autostash-api.onrender.com,autostash.up.railway.app"
_allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = _allowed_hosts_env.split(',') if _allowed_hosts_env else ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'corsheaders',

    'engine',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'autostash.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'autostash.wsgi.application'

# Uses SQLite locally by default. In production, set a DATABASE_URL env var
# (Render/Railway/Heroku all provide one automatically when you attach a
# Postgres instance) and it's picked up here instead.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# In dev (DEBUG=True) allow any origin so the standalone HTML dashboard can
# be opened as a local file and still call the API. In production, set
# CORS_ALLOWED_ORIGINS to the exact origin(s) your frontend is hosted on,
# e.g. "https://your-username.github.io,https://autostash.netlify.app"
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    _cors_origins_env = os.environ.get('CORS_ALLOWED_ORIGINS', '')
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_env.split(',') if o.strip()]

# Trust the deployed HTTPS host for POST/PATCH/DELETE (Django's CSRF check
# also looks here for admin form submissions).
_csrf_origins_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins_env.split(',') if o.strip()]

# --- AutoStash domain settings -------------------------------------------

# Minimum cash buffer AutoStash will always leave in checking, regardless
# of how much "extra" cash flow math suggests is available to sweep.
AUTOSTASH_MIN_SAFETY_BUFFER = 100.00

# Cap on how much of the "safe to sweep" amount is actually swept in a
# single daily pull (protects against over-sweeping in one go).
AUTOSTASH_MAX_DAILY_SWEEP_FRACTION = 0.25
