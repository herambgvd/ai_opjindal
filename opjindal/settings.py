import os
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy

# Initialize environment variables
env = environ.Env()
environ.Env.read_env()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = env('DJANGO_SECRET_KEY', default='your-secret-key-here')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0','172.17.41.234']

# Application definition
SYSTEM_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "rest_framework",
    "widget_tweaks",
    "drf_spectacular",
    "allauth.mfa",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
]

LOCAL_APPS = [
    'apps.users.apps.UserConfig',
    'apps.web',
    'apps.cross_counting.apps.CrossCountingConfig',
]

INSTALLED_APPS = SYSTEM_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    "allauth.account.middleware.AccountMiddleware",
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'opjindal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',  # Added for media files
            ],
        },
    },
]

WSGI_APPLICATION = 'opjindal.wsgi.application'

# Database with TimescaleDB
DATABASES = {
    "default": {
        "ENGINE": "timescale.db.backends.postgresql",
        "NAME": env("DJANGO_DATABASE_NAME", default="ai_op_jindal"),
        "USER": env("DJANGO_DATABASE_USER", default="postgres"),
        "PASSWORD": env("DJANGO_DATABASE_PASSWORD", default="Gvd@6001"),
        "HOST": env("DJANGO_DATABASE_HOST", default="localhost"),
        "PORT": env("DJANGO_DATABASE_PORT", default="5433"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # Indian Standard Time (UTC+5:30)
USE_TZ = True  # Keep timezone-aware datetimes
USE_I18N = True
USE_L10N = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / "static_root"

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
AUTH_USER_MODEL = "users.CustomUser"
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"

# Allauth setup

# Custom adapter for email-as-username & no signup
ACCOUNT_ADAPTER = "apps.users.adapter.AccountAdapter"

# Only allow email-based login
ACCOUNT_LOGIN_METHODS = {"email"}

# Signup fields: email (required), password (required once)
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]

# Email verification optional (you can change to "mandatory" if required)
ACCOUNT_EMAIL_VERIFICATION = "optional"

# Email behavior
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False  # Don't send forgot password emails to unknown users
ACCOUNT_CONFIRM_EMAIL_ON_GET = True  # Confirm email immediately when clicked
ACCOUNT_UNIQUE_EMAIL = True  # Disallow duplicate emails

# Session behavior
ACCOUNT_SESSION_REMEMBER = True  # Keep users logged in
ACCOUNT_LOGOUT_ON_GET = True  # Logout without POST

# Automatically login after email confirmation
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

# Enable code-based login (magic links or verification codes)
ACCOUNT_LOGIN_BY_CODE_ENABLED = True

ACCOUNT_FORMS = {
    "signup": "apps.users.forms.TeamSignupForm",
    "login": "apps.users.forms.UserLoginForm",
    "change_password": "apps.users.forms.PasswordChangeForm",
    "set_password": "apps.users.forms.PasswordSetForm",
    "reset_password": "apps.users.forms.PasswordResetForm",
    "reset_password_from_key": "apps.users.forms.PasswordResetKeyForm",
}

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # swap these to use manifest storage to bust cache when files change
        # note: this may break image references in sass/css files which is why it is not enabled by default
        # "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
SITE_ID = 1

# DRF config
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 100,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "clarify",
    "DESCRIPTION": "AI Center",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "displayOperationId": True,
    },
}

# Celery setup (using redis)
if "REDIS_URL" in env:
    REDIS_URL = env("REDIS_URL")
elif "REDIS_TLS_URL" in env:
    REDIS_URL = env("REDIS_TLS_URL")
else:
    REDIS_HOST = env("REDIS_HOST", default="localhost")
    REDIS_PORT = env("REDIS_PORT", default="6379")
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

if REDIS_URL.startswith("rediss"):
    REDIS_URL = f"{REDIS_URL}?ssl_cert_reqs=none"

CELERY_BROKER_URL = CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

PROJECT_METADATA = {
    "NAME": gettext_lazy("clarify"),
    "URL": "http://localhost:8000",
    "DESCRIPTION": gettext_lazy("AI Center"),
    "IMAGE": "https://upload.wikimedia.org/wikipedia/commons/2/20/PEO-pegasus_black.svg",
    "KEYWORDS": "SaaS, django",
    "CONTACT_EMAIL": "support@geniusvision.in",
}

USE_HTTPS_IN_ABSOLUTE_URLS = env.bool("USE_HTTPS_IN_ABSOLUTE_URLS", default=False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": '[{asctime}] {levelname} "{name}" {message}',
            "style": "{",
            "datefmt": "%d/%b/%Y %H:%M:%S",  # match Django server time format
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
        },
        "clarify": {
            "handlers": ["console"],
            "level": env("CLARIFY_LOG_LEVEL", default="INFO"),
        },
    },
}

# Date and Time Formatting for Indian locale
DATETIME_FORMAT = 'd/m/Y H:i:s'  # DD/MM/YYYY HH:MM:SS
DATE_FORMAT = 'd/m/Y'  # DD/MM/YYYY
TIME_FORMAT = 'H:i:s'  # HH:MM:SS

# For admin interface datetime display
DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M:%S',  # 25/12/2023 14:30:45
    '%d/%m/%Y %H:%M',  # 25/12/2023 14:30
    '%d-%m-%Y %H:%M:%S',  # 25-12-2023 14:30:45
    '%d-%m-%Y %H:%M',  # 25-12-2023 14:30
    '%Y-%m-%d %H:%M:%S',  # 2023-12-25 14:30:45 (ISO format)
    '%Y-%m-%d %H:%M',  # 2023-12-25 14:30
]

DATE_INPUT_FORMATS = [
    '%d/%m/%Y',  # 25/12/2023
    '%d-%m-%Y',  # 25-12-2023
    '%Y-%m-%d',  # 2023-12-25 (ISO format)
]

TIME_INPUT_FORMATS = [
    '%H:%M:%S',  # 14:30:45
    '%H:%M',  # 14:30
]
