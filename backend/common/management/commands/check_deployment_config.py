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
            or len(set(secret)) < 5
            or secret.startswith('django-insecure-')
            or 'replace-' in secret.lower()
        ):
            errors.append(
                'DJANGO_SECRET_KEY must be a non-placeholder value of at least '
                '50 characters with at least 5 unique characters.'
            )

        hosts = settings.ALLOWED_HOSTS
        if not hosts or '*' in hosts:
            errors.append('DJANGO_ALLOWED_HOSTS must contain explicit production host names.')
        elif any(host in {'localhost', '127.0.0.1'} for host in hosts):
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
        if settings.SECURE_HSTS_SECONDS < 31536000:
            errors.append('DJANGO_SECURE_HSTS_SECONDS must be at least 31536000.')

        database = settings.DATABASES['default']
        if database['ENGINE'].endswith('sqlite3'):
            errors.append('Production must use PostgreSQL instead of SQLite.')
        else:
            for key in ('NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
                if not database.get(key):
                    errors.append(f'Database setting {key} is required.')

        if settings.EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend':
            errors.append('EMAIL_BACKEND must use the SMTP backend.')
        for name in ('EMAIL_HOST', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'DEFAULT_FROM_EMAIL'):
            if not getattr(settings, name, None):
                errors.append(f'{name} is required.')

        if settings.USE_S3:
            for name in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_STORAGE_BUCKET_NAME'):
                if not getattr(settings, name, None):
                    errors.append(f'{name} is required when DJANGO_USE_S3=true.')
        elif not options['allow_local_storage']:
            errors.append(
                'Local media/static storage requires persistent volumes; '
                'use S3 or rerun with --allow-local-storage after mounting them.'
            )

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(f'[fail] {error}'))
            raise CommandError(f'Deployment configuration has {len(errors)} error(s).')

        storage = 'S3' if settings.USE_S3 else 'persistent local volumes'
        self.stdout.write(
            self.style.SUCCESS(
                f'Deployment configuration is ready (PostgreSQL, HTTPS, SMTP, {storage}).'
            )
        )

    @staticmethod
    def _require_https(name, values, errors):
        if not values:
            errors.append(f'{name} must not be empty.')
            return
        if any(urlparse(value).scheme != 'https' or not urlparse(value).netloc for value in values):
            errors.append(f'{name} must contain only absolute HTTPS origins.')
