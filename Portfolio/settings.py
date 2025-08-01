from pathlib import Path
import os
from decouple import config
import logging
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')  # Using decouple to fetch the SECRET_KEY from environment variables
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in the environment.")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['dhruv-portfolio-y8kt.onrender.com', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    "chat",
    "Skill",
    "home",
    "about",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'corsheaders',
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "chat_memory_cache",
    }
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", 
    'corsheaders.middleware.CorsMiddleware', 
]


CORS_ALLOWED_ORIGINS = [
    "https://dhruv-portfolio-y8kt.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


ROOT_URLCONF = "Portfolio.urls"

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATES_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "Portfolio.context_processor.fotter_data",
            ],
        },
    },
]

WSGI_APPLICATION = "Portfolio.wsgi.application"

# Configure logging for debugging database connection issues
logger = logging.getLogger(__name__)

# Log database connection parameters for debugging
logger.debug("Database configuration:")
logger.debug(f"ENGINE: {config('POSTGRES_ENGINE', default='django.db.backends.postgresql')}")
logger.debug(f"NAME: {config('POSTGRES_DATABASE', default='')}")
logger.debug(f"USER: {config('POSTGRES_USER', default='')}")
logger.debug(f"PASSWORD: {config('POSTGRES_PASSWORD', default='')}")
logger.debug(f"HOST: {config('POSTGRES_HOST', default='127.0.0.1')}")
logger.debug(f"PORT: {config('POSTGRES_PORT', default='5432')}")

# Database configuration using environment variables
DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL"),
        conn_max_age=60,
        ssl_require=True
    )
}


BLOB_READ_WRITE_TOKEN = os.getenv('BLOB_READ_WRITE_TOKEN')
# Media files (added to serve user-uploaded content like images)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Static files (CSS, JavaScript, images)
STATIC_URL = "/static/" 
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")   

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

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = not DEBUG  # Secure cookies in production (only over HTTPS)
CSRF_COOKIE_SECURE = not DEBUG  # CSRF cookies should be secure in production
X_FRAME_OPTIONS = "DENY"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration to log errors to a file
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "errors.log"),
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

PORT = os.getenv('PORT', '8000')  # Default to 8000 if PORT is not set