import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase


class ProductionSettingsValidationTests(SimpleTestCase):
    def setUp(self):
        self.temp_context = tempfile.TemporaryDirectory(prefix='farm-copilot-production-settings-')
        self.addCleanup(self.temp_context.cleanup)
        self.database_path = str(Path(self.temp_context.name) / 'application.sqlite3')
        self.production_environment = {
            'DJANGO_SETTINGS_MODULE': 'config.settings',
            'DJANGO_SECRET_KEY': secrets.token_urlsafe(48),
            'DJANGO_DEBUG': 'false',
            'DJANGO_ALLOWED_HOSTS': 'api.example.test',
            'DJANGO_USE_SQLITE': 'true',
            'SQLITE_DATABASE_PATH': self.database_path,
            'DJANGO_USE_S3': 'false',
            'CORS_ALLOWED_ORIGINS': 'https://frontend.example.test',
            'CSRF_TRUSTED_ORIGINS': 'https://frontend.example.test',
            'FRONTEND_BASE_URL': 'https://frontend.example.test',
            'SESSION_COOKIE_SECURE': 'true',
            'CSRF_COOKIE_SECURE': 'true',
            'SESSION_COOKIE_SAMESITE': 'None',
            'CSRF_COOKIE_SAMESITE': 'None',
            'DJANGO_SECURE_SSL_REDIRECT': 'true',
            'DJANGO_SECURE_HSTS_SECONDS': '86400',
            'DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS': 'false',
            'DJANGO_SECURE_HSTS_PRELOAD': 'false',
            'DJANGO_BEHIND_HTTPS_PROXY': 'false',
            'DATABASE_NAME': '',
            'DATABASE_USER': '',
            'DATABASE_PASSWORD': '',
            'DATABASE_HOST': '',
            'DATABASE_PORT': '5432',
            'AWS_ACCESS_KEY_ID': '',
            'AWS_SECRET_ACCESS_KEY': '',
            'AWS_STORAGE_BUCKET_NAME': '',
        }

    def load_settings(
        self, overrides=None, code='from django.conf import settings; print(settings.DEBUG)'
    ):
        environment = os.environ.copy()
        environment.update(self.production_environment)
        environment.update(overrides or {})
        return subprocess.run(
            [sys.executable, '-c', code],
            cwd=Path(__file__).resolve().parents[2],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def assert_rejected(self, name, value, expected_message=None):
        result = self.load_settings({name: value})
        self.assertNotEqual(result.returncode, 0, result.stdout)
        if expected_message:
            self.assertIn(expected_message, result.stderr)
        self.assertNotIn(self.production_environment['DJANGO_SECRET_KEY'], result.stderr)

    def test_production_can_use_explicit_sqlite_local_storage_without_a_proxy(self):
        result = self.load_settings()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'False')

    def test_same_origin_production_does_not_need_cors_or_csrf_allowlists(self):
        result = self.load_settings({'CORS_ALLOWED_ORIGINS': '', 'CSRF_TRUSTED_ORIGINS': ''})

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_secure_production_settings_pass_django_deployment_checks(self):
        result = self.load_settings(
            code=(
                'import django; django.setup(); '
                'from django.core.management import call_command; '
                'call_command("check", deploy=True)'
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('System check identified some issues', result.stdout)

    def test_proxy_header_is_trusted_only_when_explicitly_enabled(self):
        result = self.load_settings(
            {'DJANGO_BEHIND_HTTPS_PROXY': 'true'},
            code='from django.conf import settings; print(settings.SECURE_PROXY_SSL_HEADER)',
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "('HTTP_X_FORWARDED_PROTO', 'https')")

    def test_development_http_sqlite_defaults_remain_allowed(self):
        result = self.load_settings(
            {
                'DJANGO_DEBUG': 'true',
                'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1',
                'CORS_ALLOWED_ORIGINS': 'http://localhost:3000',
                'CSRF_TRUSTED_ORIGINS': 'http://localhost:3000',
                'FRONTEND_BASE_URL': 'http://localhost:3000',
                'SESSION_COOKIE_SECURE': 'false',
                'CSRF_COOKIE_SECURE': 'false',
                'SESSION_COOKIE_SAMESITE': 'Lax',
                'CSRF_COOKIE_SAMESITE': 'Lax',
                'DJANGO_SECURE_SSL_REDIRECT': 'false',
                'DJANGO_SECURE_HSTS_SECONDS': '0',
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'True')

    def test_missing_or_weak_secret_is_rejected_without_echoing_it(self):
        self.assert_rejected('DJANGO_SECRET_KEY', '', 'DJANGO_SECRET_KEY')
        self.assert_rejected('DJANGO_SECRET_KEY', 'weak-secret-' * 6, 'DJANGO_SECRET_KEY')

    def test_wildcard_host_and_insecure_transport_settings_are_rejected(self):
        self.assert_rejected('DJANGO_ALLOWED_HOSTS', '*', 'DJANGO_ALLOWED_HOSTS')
        self.assert_rejected('DJANGO_ALLOWED_HOSTS', '.localhost', 'DJANGO_ALLOWED_HOSTS')
        self.assert_rejected('SESSION_COOKIE_SECURE', 'false', 'SESSION_COOKIE_SECURE')
        self.assert_rejected('CSRF_COOKIE_SECURE', 'false', 'CSRF_COOKIE_SECURE')
        self.assert_rejected('DJANGO_SECURE_SSL_REDIRECT', 'false', 'DJANGO_SECURE_SSL_REDIRECT')
        self.assert_rejected('DJANGO_SECURE_HSTS_SECONDS', '0', 'DJANGO_SECURE_HSTS_SECONDS')

    def test_samesite_none_requires_secure_cookies(self):
        self.assert_rejected(
            'SESSION_COOKIE_SECURE', 'false', 'SESSION_COOKIE_SAMESITE=None requires'
        )
        self.assert_rejected('CSRF_COOKIE_SECURE', 'false', 'CSRF_COOKIE_SAMESITE=None requires')

    def test_production_origins_must_be_explicit_https_origins(self):
        self.assert_rejected(
            'CORS_ALLOWED_ORIGINS', 'http://frontend.example.test', 'CORS_ALLOWED_ORIGINS'
        )
        self.assert_rejected(
            'CORS_ALLOWED_ORIGINS', 'https://localhost:3000', 'CORS_ALLOWED_ORIGINS'
        )
        self.assert_rejected(
            'CSRF_TRUSTED_ORIGINS', 'https://*.example.test', 'CSRF_TRUSTED_ORIGINS'
        )
        self.assert_rejected(
            'CORS_ALLOWED_ORIGINS',
            'https://frontend.example.test:invalid',
            'CORS_ALLOWED_ORIGINS',
        )

    def test_production_database_and_s3_require_usable_configuration(self):
        self.assert_rejected('SQLITE_DATABASE_PATH', ':memory:', 'SQLITE_DATABASE_PATH')
        self.assert_rejected(
            'DJANGO_USE_SQLITE',
            'false',
            'DATABASE_NAME is required for PostgreSQL',
        )
        self.assert_rejected(
            'DJANGO_USE_S3',
            'true',
            'AWS_STORAGE_BUCKET_NAME is required',
        )
        result = self.load_settings(
            {
                'DJANGO_USE_S3': 'true',
                'AWS_STORAGE_BUCKET_NAME': 'private-test-bucket',
                'AWS_ACCESS_KEY_ID': 'temporary-key',
            }
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            'AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be provided together',
            result.stderr,
        )
        self.assertNotIn(self.production_environment['DJANGO_SECRET_KEY'], result.stderr)

    def test_s3_can_use_role_credentials_and_detection_storage_stays_private(self):
        result = self.load_settings(
            {
                'DJANGO_USE_S3': 'true',
                'AWS_STORAGE_BUCKET_NAME': 'private-test-bucket',
            },
            code=(
                'from django.conf import settings; '
                'from common.storage_backends import PestDetectionStorage; '
                'print(settings.AWS_DEFAULT_ACL is None, '
                'PestDetectionStorage.default_acl is None, '
                'PestDetectionStorage.querystring_auth)'
            ),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'True True True')

    def test_invalid_boolean_is_rejected_with_variable_name_only(self):
        self.assert_rejected('DJANGO_BEHIND_HTTPS_PROXY', 'perhaps', 'DJANGO_BEHIND_HTTPS_PROXY')

    def test_hsts_preload_requires_subdomains_and_one_year(self):
        self.assert_rejected('DJANGO_SECURE_HSTS_PRELOAD', 'true', 'HSTS preload requires')

    def test_non_numeric_hsts_setting_is_rejected_without_echoing_input(self):
        self.assert_rejected(
            'DJANGO_SECURE_HSTS_SECONDS', 'not-a-number', 'DJANGO_SECURE_HSTS_SECONDS'
        )
