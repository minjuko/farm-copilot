from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings
from django.test.utils import ignore_warnings


class ExternalServiceCheckCommandTests(SimpleTestCase):
    @patch.dict('os.environ', {'KAKAO_REST_API_KEY': 'secret-value'}, clear=True)
    def test_configuration_check_does_not_print_credentials(self):
        stdout = StringIO()
        call_command('check_external_services', stdout=stdout)
        output = stdout.getvalue()
        self.assertIn('kakao: configured', output)
        self.assertNotIn('secret-value', output)

    @patch(
        'common.management.commands.check_external_services.Command._check_kakao',
        return_value='sample resolved',
    )
    def test_live_provider_is_called_only_when_selected(self, check_kakao):
        stdout = StringIO()
        call_command('check_external_services', '--live', 'kakao', stdout=stdout)
        check_kakao.assert_called_once_with()
        self.assertIn('kakao: ok', stdout.getvalue())


@ignore_warnings(category=UserWarning)
class DeploymentConfigCommandTests(SimpleTestCase):
    production_settings = {
        'DEBUG': False,
        'SECRET_KEY': 'abcde' * 10,
        'ALLOWED_HOSTS': ['api.example.com'],
        'CORS_ALLOWED_ORIGINS': ['https://www.example.com'],
        'CSRF_TRUSTED_ORIGINS': ['https://www.example.com'],
        'FRONTEND_BASE_URL': 'https://www.example.com',
        'SESSION_COOKIE_SECURE': True,
        'CSRF_COOKIE_SECURE': True,
        'SECURE_SSL_REDIRECT': True,
        'SECURE_HSTS_SECONDS': 31536000,
        'DATABASES': {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'app',
                'USER': 'app',
                'PASSWORD': 'secret',
                'HOST': 'database',
                'PORT': '5432',
            }
        },
        'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'EMAIL_HOST': 'smtp.example.com',
        'EMAIL_HOST_USER': 'sender@example.com',
        'EMAIL_HOST_PASSWORD': 'secret',
        'DEFAULT_FROM_EMAIL': 'sender@example.com',
        'USE_S3': False,
    }

    @override_settings(**production_settings)
    def test_valid_config_with_persistent_local_storage_passes(self):
        stdout = StringIO()
        call_command(
            'check_deployment_config',
            '--allow-local-storage',
            stdout=stdout,
        )
        self.assertIn('Deployment configuration is ready', stdout.getvalue())

    @override_settings(**{**production_settings, 'DEBUG': True})
    def test_unsafe_config_fails(self):
        stderr = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                'check_deployment_config',
                '--allow-local-storage',
                stderr=stderr,
            )

    @override_settings(**{**production_settings, 'SECRET_KEY': 'a' * 50})
    def test_low_entropy_secret_key_fails(self):
        stderr = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                'check_deployment_config',
                '--allow-local-storage',
                stderr=stderr,
            )
