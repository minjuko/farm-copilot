from ipaddress import ip_address
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Validate security and infrastructure settings before deployment.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--allow-local-storage',
            action='store_true',
            help='Allow local media/static storage when persistent volumes exist.',
        )

    def handle(self, *args, **options):
        errors = []

        if settings.DEBUG:
            errors.append('DJANGO_DEBUG must be false.')

        secret = settings.SECRET_KEY
        if (
            len(secret) < 50
            or len(set(secret)) < 16
            or any(
                marker in secret.lower() for marker in ('django-insecure-', 'replace-', 'change-me')
            )
        ):
            errors.append(
                'DJANGO_SECRET_KEY must be a non-placeholder value of at least '
                '50 characters with at least 16 unique characters.'
            )

        hosts = settings.ALLOWED_HOSTS
        if not hosts or '*' in hosts:
            errors.append('DJANGO_ALLOWED_HOSTS must contain explicit production host names.')
        elif any(self._is_loopback_host(host) for host in hosts):
            errors.append('DJANGO_ALLOWED_HOSTS must not contain local-only hosts.')

        self._require_https('CORS_ALLOWED_ORIGINS', settings.CORS_ALLOWED_ORIGINS, errors)
        self._require_https('CSRF_TRUSTED_ORIGINS', settings.CSRF_TRUSTED_ORIGINS, errors)
        self._require_https('FRONTEND_BASE_URL', [settings.FRONTEND_BASE_URL], errors)

        if not settings.SESSION_COOKIE_SECURE:
            errors.append('SESSION_COOKIE_SECURE must be true.')
        if not settings.CSRF_COOKIE_SECURE:
            errors.append('CSRF_COOKIE_SECURE must be true.')
        if not settings.SECURE_SSL_REDIRECT:
            errors.append('DJANGO_SECURE_SSL_REDIRECT must be true.')
        if settings.SECURE_HSTS_SECONDS <= 0:
            errors.append('DJANGO_SECURE_HSTS_SECONDS must be greater than zero.')
        if settings.SECURE_HSTS_PRELOAD and (
            not settings.SECURE_HSTS_INCLUDE_SUBDOMAINS or settings.SECURE_HSTS_SECONDS < 31536000
        ):
            errors.append('HSTS preload requires includeSubDomains and at least 31536000 seconds.')

        for name, value, secure in (
            (
                'SESSION_COOKIE_SAMESITE',
                settings.SESSION_COOKIE_SAMESITE,
                settings.SESSION_COOKIE_SECURE,
            ),
            (
                'CSRF_COOKIE_SAMESITE',
                settings.CSRF_COOKIE_SAMESITE,
                settings.CSRF_COOKIE_SECURE,
            ),
        ):
            if value not in {'Strict', 'Lax', 'None'}:
                errors.append(f'{name} must be Strict, Lax, or None.')
            if value == 'None' and not secure:
                errors.append(f'{name}=None requires its corresponding Secure cookie setting.')

        database = settings.DATABASES['default']
        if database['ENGINE'].endswith('sqlite3'):
            database_name = str(database.get('NAME') or '')
            if not database_name or database_name == ':memory:':
                errors.append('SQLITE_DATABASE_PATH must identify a persistent file.')
        else:
            for key in ('NAME', 'HOST'):
                if not database.get(key):
                    errors.append(f'Database setting {key} is required.')
            port = database.get('PORT')
            if port:
                try:
                    valid_port = 1 <= int(port) <= 65535
                except (TypeError, ValueError):
                    valid_port = False
                if not valid_port:
                    errors.append('Database setting PORT must be between 1 and 65535.')

        if settings.USE_S3:
            if not getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None):
                errors.append('AWS_STORAGE_BUCKET_NAME is required when DJANGO_USE_S3=true.')
            if bool(getattr(settings, 'AWS_ACCESS_KEY_ID', None)) != bool(
                getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
            ):
                errors.append(
                    'AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be provided together.'
                )
        elif not options['allow_local_storage']:
            errors.append(
                'Local media/static storage requires persistent volumes; '
                'use S3 or rerun with --allow-local-storage after mounting them.'
            )

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(f'[fail] {error}'))
            raise CommandError(f'Deployment configuration has {len(errors)} error(s).')

        database = (
            'SQLite'
            if settings.DATABASES['default']['ENGINE'].endswith('sqlite3')
            else 'PostgreSQL'
        )
        storage = 'S3' if settings.USE_S3 else 'persistent local volumes'
        self.stdout.write(
            self.style.SUCCESS(f'Deployment configuration is ready ({database}, HTTPS, {storage}).')
        )

    def _require_https(self, name, values, errors):
        if not values:
            return
        for value in values:
            try:
                parsed = urlparse(value)
                parsed.port
            except ValueError:
                errors.append(f'{name} must contain only valid absolute HTTPS origins/URLs.')
                return
            if (
                parsed.scheme != 'https'
                or not parsed.hostname
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or '*' in value
                or (name != 'FRONTEND_BASE_URL' and self._is_loopback_host(parsed.hostname or ''))
                or (name != 'FRONTEND_BASE_URL' and parsed.path not in {'', '/'})
            ):
                errors.append(f'{name} must contain only valid absolute HTTPS origins/URLs.')
                return

    @staticmethod
    def _is_loopback_host(host):
        normalized = host.lower().lstrip('.').strip('[]')
        if normalized == 'localhost' or normalized.endswith('.localhost'):
            return True
        try:
            return ip_address(normalized).is_loopback
        except ValueError:
            return False
