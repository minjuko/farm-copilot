from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings


class CapabilityApiTests(SimpleTestCase):
    @override_settings(
        SOIL_SERVICE_ENABLED=True,
        PREDICTION_SERVICE_ENABLED=True,
        CHATBOT_ENABLED=False,
        USE_S3=False,
    )
    @patch.dict('os.environ', {}, clear=True)
    @patch('pathlib.Path.is_file', return_value=False)
    def test_missing_configuration_is_reported_without_secret_details(
        self, _artifact_available
    ):
        response = self.client.get('/api/capabilities/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['soil']['status'], 'limited')
        self.assertEqual(payload['prediction']['status'], 'limited')
        self.assertEqual(payload['chatbot']['status'], 'archived')
        self.assertEqual(payload['detection']['status'], 'limited')
        self.assertEqual(payload['email']['status'], 'limited')
        self.assertEqual(payload['storage']['status'], 'local')
        self.assertNotContains(response, 'API_KEY')

    @override_settings(
        SOIL_SERVICE_ENABLED=True,
        PREDICTION_SERVICE_ENABLED=True,
        CHATBOT_ENABLED=True,
        USE_S3=True,
    )
    @patch.dict('os.environ', {
        'KAKAO_REST_API_KEY': 'configured',
        'DATA_GO_KR_SOIL_SERVICE_KEY': 'configured',
        'DATA_GO_KR_FERTILIZER_V2_SERVICE_KEY': 'configured',
        'DATA_GO_KR_WEATHER_SERVICE_KEY': 'configured',
        'DATA_GO_KR_MARKET_SERVICE_KEY': 'configured',
        'OPENAI_API_KEY': 'configured',
        'CHROMA_DB_PATH': 'configured',
        'EMAIL_HOST_USER': 'configured@example.com',
        'EMAIL_HOST_PASSWORD': 'configured',
        'DEFAULT_FROM_EMAIL': 'configured@example.com',
    }, clear=True)
    @patch('selfchatbot.views.vector_index_available', return_value=True)
    @patch('selfchatbot.views.CHATBOT_DEPENDENCIES_AVAILABLE', True)
    @patch('pathlib.Path.is_file', return_value=True)
    def test_configured_services_are_reported_available(
        self, _model_available, _index_available
    ):
        payload = self.client.get('/api/capabilities/').json()

        self.assertTrue(payload['soil']['available'])
        self.assertTrue(payload['prediction']['available'])
        self.assertTrue(payload['chatbot']['available'])
        self.assertTrue(payload['detection']['available'])
        self.assertTrue(payload['email']['available'])
        self.assertEqual(payload['storage']['status'], 's3')


class ExternalServiceCheckCommandTests(SimpleTestCase):
    @patch.dict('os.environ', {'KAKAO_REST_API_KEY': 'secret-value'}, clear=True)
    def test_configuration_check_does_not_print_credentials(self):
        stdout = StringIO()
        call_command('check_external_services', stdout=stdout)
        output = stdout.getvalue()
        self.assertIn('kakao: configured', output)
        self.assertNotIn('secret-value', output)

    @patch(
        'soil.management.commands.check_external_services.Command._check_kakao',
        return_value='sample resolved',
    )
    def test_live_provider_is_called_only_when_selected(self, check_kakao):
        stdout = StringIO()
        call_command('check_external_services', '--live', 'kakao', stdout=stdout)
        check_kakao.assert_called_once_with()
        self.assertIn('kakao: ok', stdout.getvalue())


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
        'DATABASES': {'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'app',
            'USER': 'app',
            'PASSWORD': 'secret',
            'HOST': 'database',
            'PORT': '5432',
        }},
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
        with self.assertRaises(CommandError):
            call_command('check_deployment_config', '--allow-local-storage')

    @override_settings(**{**production_settings, 'SECRET_KEY': 'a' * 50})
    def test_low_entropy_secret_key_fails(self):
        with self.assertRaises(CommandError):
            call_command('check_deployment_config', '--allow-local-storage')
