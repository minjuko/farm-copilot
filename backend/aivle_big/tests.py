from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
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
