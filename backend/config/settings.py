import os
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise ImproperlyConfigured(f'{name} must be a boolean value.')


def env_list(name, default=''):
    return [value.strip() for value in os.getenv(name, default).split(',') if value.strip()]


def env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f'{name} must be an integer.') from exc


def _valid_absolute_url(value, allowed_schemes, allow_path):
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        return False
    return bool(
        parsed.scheme in allowed_schemes
        and parsed.hostname
        and parsed.netloc
        and parsed.username is None
        and parsed.password is None
        and (allow_path or parsed.path in {'', '/'})
        and not parsed.query
        and not parsed.fragment
        and '*' not in value
    )


def _is_loopback_host(host):
    normalized = host.lower().lstrip('.').strip('[]')
    if normalized == 'localhost' or normalized.endswith('.localhost'):
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


# Keep the production secret key outside source control.
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY is required.')

# Debug output must remain disabled in production.
DEBUG = env_bool('DJANGO_DEBUG', False)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')


# Applications

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'common.apps.CommonConfig',
    'storages',
    'accounts.apps.AccountsConfig',
    'community',
    'chatbot.apps.ChatbotConfig',
    'corsheaders',
    'rest_framework',
    'prediction',
    'detect',
    'soil',
]


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'common.middleware.CustomExceptionMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [f'{BASE_DIR}/templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:3000' if DEBUG else '')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000' if DEBUG else '')
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600

# Cookie security
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', not DEBUG)
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax' if DEBUG else 'None')
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax' if DEBUG else 'None')
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SECURE_HSTS_SECONDS = env_int('DJANGO_SECURE_HSTS_SECONDS', 0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
if env_bool('DJANGO_BEHIND_HTTPS_PROXY', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Database
USE_SQLITE = env_bool('DJANGO_USE_SQLITE', False)

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': Path(os.getenv('SQLITE_DATABASE_PATH', BASE_DIR / 'db.sqlite3')),
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME'),
            'USER': os.getenv('DATABASE_USER'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD'),
            'HOST': os.getenv('DATABASE_HOST'),
            'PORT': os.getenv('DATABASE_PORT'),
            'OPTIONS': {
                'options': '-c client_encoding=UTF8',
            },
        },
    }

DATABASE_ROUTERS = ['config.db_routers.SchemaRouter']
AUTH_USER_MODEL = 'login.User'


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

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
    if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '10'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000' if DEBUG else '')

# Optional agriculture chatbot runtime. The feature remains disabled unless it
# is explicitly enabled and all provider/runtime artifacts are configured.
CHATBOT_ENABLED = env_bool('CHATBOT_ENABLED', False)
CHATBOT_LLM_MODEL = os.getenv('CHATBOT_LLM_MODEL', 'gpt-4o-mini')
CHATBOT_EMBEDDING_MODEL = os.getenv('CHATBOT_EMBEDDING_MODEL', 'text-embedding-3-small')
CHATBOT_COLLECTION_NAME = os.getenv('CHATBOT_COLLECTION_NAME', 'agriculture-knowledge')
YOLO_AUGMENTED_INFERENCE = env_bool('YOLO_AUGMENTED_INFERENCE', True)
SOIL_SERVICE_ENABLED = env_bool('SOIL_SERVICE_ENABLED', True)
PREDICTION_SERVICE_ENABLED = env_bool('PREDICTION_SERVICE_ENABLED', True)


# Internationalization

LANGUAGE_CODE = 'ko-kr'

TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True


# Static files

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
DETECTION_IMAGE_ROOT = Path(
    os.getenv('DETECTION_IMAGE_ROOT', str(BASE_DIR / 'private_media'))
).resolve()

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

USE_S3 = env_bool('DJANGO_USE_S3', False)

if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_LOCATION = os.getenv('AWS_LOCATION', '')
    AWS_DEFAULT_ACL = None
    STATIC_LOCATION = 'static'
    MEDIA_LOCATION = 'media'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/'
    STORAGES = {
        'default': {'BACKEND': 'common.storage_backends.MediaStorage'},
        'staticfiles': {'BACKEND': 'common.storage_backends.StaticStorage'},
    }
else:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


def _production_configuration_errors():
    errors = []
    if DEBUG:
        return errors

    secret = SECRET_KEY.lower()
    if (
        len(SECRET_KEY) < 50
        or len(set(SECRET_KEY)) < 16
        or any(marker in secret for marker in ('django-insecure-', 'replace-', 'change-me'))
    ):
        errors.append(
            'DJANGO_SECRET_KEY must be a strong, non-placeholder value of at least 50 characters.'
        )

    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        errors.append('DJANGO_ALLOWED_HOSTS must contain explicit host names and cannot contain *.')
    elif any(_is_loopback_host(host) for host in ALLOWED_HOSTS):
        errors.append('DJANGO_ALLOWED_HOSTS cannot contain local-only hosts in production.')

    if not SESSION_COOKIE_SECURE:
        errors.append('SESSION_COOKIE_SECURE must be true when DJANGO_DEBUG=false.')
    if not CSRF_COOKIE_SECURE:
        errors.append('CSRF_COOKIE_SECURE must be true when DJANGO_DEBUG=false.')
    if not SECURE_SSL_REDIRECT:
        errors.append('DJANGO_SECURE_SSL_REDIRECT must be true when DJANGO_DEBUG=false.')
    if SECURE_HSTS_SECONDS <= 0:
        errors.append(
            'DJANGO_SECURE_HSTS_SECONDS must be greater than zero when DJANGO_DEBUG=false.'
        )
    if SECURE_HSTS_PRELOAD and (
        not SECURE_HSTS_INCLUDE_SUBDOMAINS or SECURE_HSTS_SECONDS < 31536000
    ):
        errors.append('HSTS preload requires includeSubDomains and at least 31536000 seconds.')

    for name, value in (
        ('SESSION_COOKIE_SAMESITE', SESSION_COOKIE_SAMESITE),
        ('CSRF_COOKIE_SAMESITE', CSRF_COOKIE_SAMESITE),
    ):
        if value not in {'Strict', 'Lax', 'None'}:
            errors.append(f'{name} must be Strict, Lax, or None.')
        if value == 'None' and not (
            SESSION_COOKIE_SECURE if name == 'SESSION_COOKIE_SAMESITE' else CSRF_COOKIE_SECURE
        ):
            errors.append(f'{name}=None requires its corresponding Secure cookie setting.')

    for name, origins in (
        ('CORS_ALLOWED_ORIGINS', CORS_ALLOWED_ORIGINS),
        ('CSRF_TRUSTED_ORIGINS', CSRF_TRUSTED_ORIGINS),
    ):
        for origin in origins:
            parsed = urlsplit(origin)
            if not _valid_absolute_url(origin, {'https'}, allow_path=False) or _is_loopback_host(
                parsed.hostname or ''
            ):
                errors.append(
                    f'{name} entries must be explicit HTTPS origins without paths or wildcards.'
                )
                break

    if not _valid_absolute_url(FRONTEND_BASE_URL, {'https'}, allow_path=True):
        errors.append('FRONTEND_BASE_URL must be an absolute HTTPS URL in production.')

    database = DATABASES['default']
    if database['ENGINE'].endswith('sqlite3'):
        database_name = str(database.get('NAME') or '')
        sqlite_path = os.getenv('SQLITE_DATABASE_PATH', '').strip()
        if not sqlite_path or not database_name or database_name == ':memory:':
            errors.append('SQLITE_DATABASE_PATH must identify a persistent file in production.')
    else:
        for key in ('NAME', 'HOST'):
            if not database.get(key):
                errors.append(f'DATABASE_{key} is required for PostgreSQL.')
        port = database.get('PORT')
        if port:
            try:
                valid_port = 1 <= int(port) <= 65535
            except (TypeError, ValueError):
                valid_port = False
            if not valid_port:
                errors.append('DATABASE_PORT must be between 1 and 65535.')

    if USE_S3:
        if not AWS_STORAGE_BUCKET_NAME:
            errors.append('AWS_STORAGE_BUCKET_NAME is required when DJANGO_USE_S3=true.')
        if bool(AWS_ACCESS_KEY_ID) != bool(AWS_SECRET_ACCESS_KEY):
            errors.append('AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be provided together.')

    return errors


_production_errors = _production_configuration_errors()
if _production_errors:
    raise ImproperlyConfigured('Invalid production configuration: ' + ' '.join(_production_errors))
