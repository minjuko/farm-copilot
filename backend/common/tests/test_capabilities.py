from unittest.mock import patch

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
        'AWS_ACCESS_KEY_ID': 'configured',
        'AWS_SECRET_ACCESS_KEY': 'configured',
        'AWS_STORAGE_BUCKET_NAME': 'configured-bucket',
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

    @override_settings(USE_S3=True)
    @patch.dict('os.environ', {}, clear=True)
    def test_incomplete_s3_configuration_is_reported_as_limited(self):
        payload = self.client.get('/api/capabilities/').json()

        self.assertEqual(payload['storage'], {
            'status': 'limited',
            'available': False,
            'reason': 'not_configured',
        })
