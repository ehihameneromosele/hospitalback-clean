# settings.py - FIXED
import os
import time
import logging
from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

# ========== SECURITY ==========
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,.onrender.com', cast=Csv())

ROOT_URLCONF = 'api.urls'
WSGI_APPLICATION = 'api.wsgi.application'

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

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'storages',
    'django_filters',
    'django_redis',

    # local apps
    'users.apps.UsersConfig',
    'hospital.apps.HospitalConfig',
    'social_django',
]

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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

# ========== DATABASE ==========
# Use DATABASE_URL env var when set (Render injects this automatically).
# Falls back to SQLite locally when DATABASE_URL is absent from .env.
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    logger.info("✅ Using PostgreSQL via DATABASE_URL")
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }
    logger.info("⚠️  DATABASE_URL not set — using local SQLite fallback")

# ========== EMAIL ==========
EMAIL_BACKEND    = config('EMAIL_BACKEND',    default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST       = config('EMAIL_HOST',       default='smtp.gmail.com')
EMAIL_PORT       = config('EMAIL_PORT',       default=587, cast=int)
EMAIL_USE_TLS    = config('EMAIL_USE_TLS',    default=True, cast=bool)
EMAIL_HOST_USER  = config('EMAIL_HOST_USER',  default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# ========== CACHE ==========
# Uses Redis on Render (REDIS_URL env var is set there).
# Falls back to local memory cache when REDIS_URL is absent —
# no Redis installation required for local development.
REDIS_URL = os.environ.get('REDIS_URL', '')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND':  'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS':          'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT':         5,
                'IGNORE_EXCEPTIONS':      True,  # cache miss on Redis error, never crash
            },
            'KEY_PREFIX': 'hospital',
            'TIMEOUT':    300,
        }
    }
    SESSION_ENGINE       = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS  = 'default'
    logger.info("✅ Redis cache configured")
else:
    CACHES = {
        'default': {
            'BACKEND':  'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'hospital-local',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    logger.info("⚠️  REDIS_URL not set — using local memory cache")

# ========== CACHE UTILITY ==========
def safe_cache_delete_pattern(pattern: str) -> None:
    """Delete a cache key pattern — silently skips if backend doesn't support it."""
    from django.core.cache import cache
    try:
        cache.delete_pattern(pattern)
        logger.debug("Deleted cache pattern: %s", pattern)
    except AttributeError:
        # LocMemCache doesn't support delete_pattern — safe to ignore locally
        pass
    except Exception as e:
        logger.error("Error deleting cache pattern %s: %s", pattern, e)

# ========== CELERY ==========
CELERY_BROKER_URL         = REDIS_URL if REDIS_URL else 'memory://'
CELERY_RESULT_BACKEND     = REDIS_URL if REDIS_URL else 'cache+memory://'
CELERY_ACCEPT_CONTENT     = ['json']
CELERY_TASK_SERIALIZER    = 'json'
CELERY_RESULT_SERIALIZER  = 'json'
CELERY_TIMEZONE           = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER  = not bool(REDIS_URL)   # run tasks inline locally
CELERY_TASK_EAGER_PROPAGATES       = True
CELERY_WORKER_MAX_TASKS_PER_CHILD  = 1000
CELERY_WORKER_PREFETCH_MULTIPLIER  = 1

if REDIS_URL:
    logger.info("✅ Celery configured with Redis broker")
else:
    logger.warning("⚠️  No Redis URL — Celery tasks run synchronously (local mode)")

# ========== STATIC FILES ==========
STATIC_URL    = '/static/'
STATIC_ROOT   = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE      = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS   = True
WHITENOISE_MANIFEST_STRICT  = False
WHITENOISE_ALLOW_ALL_ORIGINS = True

# ========== MEDIA / S3 ==========
USE_S3 = config('USE_S3', default=False, cast=bool)

AWS_ACCESS_KEY_ID       = config('AWS_ACCESS_KEY_ID',       default='')
AWS_SECRET_ACCESS_KEY   = config('AWS_SECRET_ACCESS_KEY',   default='')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_REGION_NAME      = config('AWS_S3_REGION_NAME',      default='eu-north-1')

AWS_CREDENTIALS_PROVIDED = all([
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
])

if AWS_CREDENTIALS_PROVIDED and USE_S3:
    logger.info('✅ AWS S3 storage active')
    AWS_S3_USE_SSL          = True
    AWS_S3_SECURE_URLS      = True
    AWS_S3_FILE_OVERWRITE   = False
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL         = 'public-read'
    AWS_QUERYSTRING_AUTH    = False
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    DEFAULT_FILE_STORAGE    = 'hospital.storage_backends.MediaStorage'
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/'
else:
    logger.warning('⚠️  S3 not configured — using local filesystem storage')
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL  = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

BASE_URL     = config('BASE_URL',     default='https://hospitalback-clean-0fre.onrender.com')
FRONTEND_URL = config('FRONTEND_URL', default='https://ettahospitalclone.vercel.app')

# ========== JWT ==========
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':   timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME':  timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':   True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN':       True,
    'ALGORITHM':               'HS256',
    'SIGNING_KEY':             SECRET_KEY,
    'VERIFYING_KEY':           None,
    'AUTH_HEADER_TYPES':       ('Bearer',),
    'AUTH_HEADER_NAME':        'HTTP_AUTHORIZATION',
    'USER_ID_FIELD':           'id',
    'USER_ID_CLAIM':           'user_id',
}

# ========== DRF ==========
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

if not DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
        'rest_framework.renderers.JSONRenderer',
    ]

# ========== CORS ==========
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    cast=Csv(),
    default='http://localhost:3000,https://ettahospitalclone.vercel.app',
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    cast=Csv(),
    default='http://localhost:3000,https://ettahospitalclone.vercel.app,https://*.onrender.com',
)

# ========== SESSION SECURITY ==========
if not DEBUG:
    SESSION_COOKIE_SECURE        = True
    SESSION_COOKIE_HTTPONLY      = True
    SESSION_COOKIE_SAMESITE      = 'Lax'
    CSRF_COOKIE_SECURE           = True
    CSRF_COOKIE_SAMESITE         = 'Lax'
    SECURE_SSL_REDIRECT          = True
    SECURE_HSTS_SECONDS          = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD          = True

# ========== SOCIAL AUTH ==========
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY    = config('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY',    default='')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = config('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', default='')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE  = ['email', 'profile']

# ========== DB CONNECTION RETRY (for transient drops) ==========
class DatabaseConnectionRetry:
    """
    Retries a dropped DB connection with exponential backoff.
    This is NOT a cold-start solution — use UptimeRobot for that.
    """
    @staticmethod
    def connect_with_retry(max_retries: int = 8, initial_delay: float = 2.0) -> bool:
        from django.db import connections
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                conn = connections['default']
                conn.ensure_connection()
                logger.info("✅ DB connected on attempt %d", attempt + 1)
                return True
            except Exception as exc:
                logger.warning(
                    "⚠️  DB attempt %d/%d failed: %s — retrying in %.0fs",
                    attempt + 1, max_retries, exc, delay,
                )
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay = min(delay * 2, 60)   # cap at 60 s per wait
        logger.error("❌ DB connection failed after %d retries", max_retries)
        return False

# ========== LOGGING ==========
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level':    'INFO',
    },
    'loggers': {
        'django': {
            'handlers':  ['console'],
            'level':     'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'level': 'WARNING',
        },
        'hospital': {
            'handlers':  ['console'],
            'level':     'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'users': {
            'handlers':  ['console'],
            'level':     'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ========== UPLOAD LIMITS ==========
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========== STARTUP BANNER ==========
logger.info("=" * 50)
logger.info("🚀 Hospital Backend Starting Up")
logger.info("🔧 DEBUG:    %s", DEBUG)
logger.info("🌍 Hosts:    %s", ALLOWED_HOSTS)
logger.info("🗄️  Database: %s", DATABASES['default']['ENGINE'])
logger.info("⚡ Redis:    %s", bool(REDIS_URL))
logger.info("☁️  S3:       %s", AWS_CREDENTIALS_PROVIDED and USE_S3)
logger.info("🔗 Base URL: %s", BASE_URL)
logger.info("=" * 50)