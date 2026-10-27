"""Strictly isolated settings for local browser E2E runs.

This module refuses to start unless the caller provides a unique temporary
root created for this purpose. It keeps the ordinary development settings
unchanged while routing database and uploaded media writes away from them.
"""

import os
import stat
import tempfile
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403

_MARKER_NAME = '.farm-copilot-e2e-root'
_ORIGIN = 'http://localhost:3000'


def _resolved(path):
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate  # noqa: F405
    return candidate.resolve()


def _is_within(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _is_link_or_junction(path):
    if path.is_symlink():
        return True
    if hasattr(os.path, 'isjunction') and os.path.isjunction(path):
        return True
    reparse_point = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
    file_attributes = getattr(path.stat(), 'st_file_attributes', 0) if path.exists() else 0
    return bool(reparse_point and file_attributes & reparse_point)


if os.getenv('FARM_COPILOT_E2E_MODE') != '1':
    raise ImproperlyConfigured('FARM_COPILOT_E2E_MODE=1 is required for E2E settings.')

_root_value = os.getenv('FARM_COPILOT_E2E_ROOT')
if not _root_value:
    raise ImproperlyConfigured(
        'FARM_COPILOT_E2E_ROOT must point to a dedicated temporary directory.'
    )
_root_input = Path(_root_value)
if not _root_input.is_absolute() or _is_link_or_junction(_root_input):
    raise ImproperlyConfigured('The E2E root must be an absolute, non-symlink path.')
E2E_ROOT = _root_input.resolve()
_project_root = BASE_DIR.parent.resolve()  # noqa: F405
_system_temp_root = Path(tempfile.gettempdir()).resolve()
if _is_within(E2E_ROOT, _project_root) or _is_within(_project_root, E2E_ROOT):
    raise ImproperlyConfigured('The E2E root must be outside the repository.')
if E2E_ROOT.parent != _system_temp_root:
    raise ImproperlyConfigured(
        'The E2E root must be a dedicated child of the system temporary directory.'
    )

if not E2E_ROOT.name.startswith('farm-copilot-e2e-'):
    raise ImproperlyConfigured('The E2E root must use the farm-copilot-e2e-* name.')

_marker = E2E_ROOT / _MARKER_NAME
if not E2E_ROOT.is_dir() or _is_link_or_junction(_marker) or not _marker.is_file():
    raise ImproperlyConfigured(
        'The E2E root or its marker is missing or unsafe; refusing to start.'
    )
if _marker.read_text(encoding='utf-8') != 'isolated-local-e2e\n':
    raise ImproperlyConfigured('The E2E root marker is missing or invalid; refusing to start.')

# A valid marker alone must not authorize reuse of an old or populated directory.
_expected_root_entries = {_MARKER_NAME, 'db', 'media', 'private_media'}
if {entry.name for entry in E2E_ROOT.iterdir()} != _expected_root_entries:
    raise ImproperlyConfigured(
        'The E2E root must contain only its marker and fresh db/media/private_media directories.'
    )
for _directory_name in ('db', 'media', 'private_media'):
    _directory = E2E_ROOT / _directory_name
    if _is_link_or_junction(_directory) or not _directory.is_dir() or any(_directory.iterdir()):
        raise ImproperlyConfigured(
            'The E2E db/media/private_media directories must be real, empty directories.'
        )

_database_path = (E2E_ROOT / 'db' / 'e2e.sqlite3').resolve()
_media_path = (E2E_ROOT / 'media').resolve()
_private_media_path = (E2E_ROOT / 'private_media').resolve()
if not all(
    _is_within(path, E2E_ROOT) for path in (_database_path, _media_path, _private_media_path)
):
    raise ImproperlyConfigured('E2E database and media paths must remain inside the E2E root.')

_existing_media_path = Path(MEDIA_ROOT).resolve()  # noqa: F405
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':  # noqa: F405
    _existing_database_path = _resolved(DATABASES['default']['NAME'])  # noqa: F405
    if _database_path == _existing_database_path:
        raise ImproperlyConfigured(
            'E2E database path must differ from the configured development database.'
        )
if _media_path == _existing_media_path:
    raise ImproperlyConfigured(
        'E2E media path must differ from the configured development media root.'
    )
if _is_within(_media_path, _existing_media_path) or _is_within(_existing_media_path, _media_path):
    raise ImproperlyConfigured(
        'E2E media path must not overlap the configured development media root.'
    )
_existing_private_media_path = Path(DETECTION_IMAGE_ROOT).resolve()  # noqa: F405
if (
    _private_media_path == _existing_private_media_path
    or _is_within(_private_media_path, _existing_private_media_path)
    or _is_within(_existing_private_media_path, _private_media_path)
):
    raise ImproperlyConfigured(
        'E2E private media path must not overlap the configured detection image root.'
    )

DATABASES = {  # noqa: F405
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _database_path,
    }
}
MEDIA_ROOT = _media_path
DETECTION_IMAGE_ROOT = _private_media_path
DEBUG = True
USE_S3 = False
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
CORS_ALLOWED_ORIGINS = [_ORIGIN]
CSRF_TRUSTED_ORIGINS = [_ORIGIN]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CHATBOT_ENABLED = False
