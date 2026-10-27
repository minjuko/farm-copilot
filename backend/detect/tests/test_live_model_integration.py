"""Opt-in CPU integration test for the real, locally provisioned YOLO artifact."""

import os
import tempfile
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import User
from detect.artifact import resolve_model_path
from detect.models import PestDetection


@skipUnless(
    os.getenv('RUN_LIVE_DETECTION_INTEGRATION') == '1',
    'Set RUN_LIVE_DETECTION_INTEGRATION=1 to use the real local model.',
)
class LiveModelDetectionIntegrationTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory(prefix='farm-copilot-live-media-')
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_dir.cleanup)
        self.private_storage_dir = tempfile.TemporaryDirectory(
            prefix='farm-copilot-live-private-media-'
        )
        self.image_storage = PestDetection._meta.get_field('image').storage
        self.original_storage_location = self.image_storage.location
        self.image_storage.location = self.private_storage_dir.name
        self.addCleanup(self.private_storage_dir.cleanup)
        self.addCleanup(setattr, self.image_storage, 'location', self.original_storage_location)

        call_command('seed_detection_catalog', verbosity=0)
        self.user = User.objects.create_user(
            username='live-detection-test',
            email='live-detection-test@example.com',
            password='test-password',
        )
        self.client.force_login(self.user)

    def test_real_model_upload_persists_and_reads_owned_detection(self):
        available = self.client.get('/api/capabilities/')
        self.assertEqual(available.status_code, 200)
        self.assertTrue(available.json()['detection']['available'])

        missing_model = Path(self.media_dir.name) / 'missing-live-test-model.pt'
        with patch.dict(os.environ, {'YOLO_MODEL_PATH': str(missing_model)}):
            unavailable = self.client.get('/api/capabilities/')
        self.assertEqual(unavailable.json()['detection']['status'], 'limited')
        self.assertEqual(unavailable.json()['detection']['reason'], 'model_missing')

        with patch.dict(
            os.environ,
            {'YOLO_MODEL_PATH': str(resolve_model_path())},
        ):
            recovered = self.client.get('/api/capabilities/')
        self.assertTrue(recovered.json()['detection']['available'])

        image_path = (
            Path(__file__).resolve().parents[2]
            / 'static'
            / 'detect'
            / 'reference'
            / 'cucumber-downy-mildew.png'
        )
        with image_path.open('rb') as image_stream:
            image = SimpleUploadedFile(
                image_path.name,
                image_stream.read(),
                content_type='image/png',
            )
        response = self.client.post('/detect/upload/', {'image': image})

        self.assertEqual(response.status_code, 200, response.content.decode())
        result = response.json()
        self.assertIsInstance(result['session_id'], int)
        self.assertTrue(result['pest_name'])
        self.assertGreaterEqual(result['confidence'], 0)
        self.assertLessEqual(result['confidence'], 100)
        self.assertEqual(PestDetection.objects.filter(user=self.user).count(), 1)

        private_image = self.client.get(result['user_image_url'])
        self.assertEqual(private_image.status_code, 200)
        self.assertTrue(private_image['Content-Type'].startswith('image/'))
        self.assertEqual(private_image['Cache-Control'], 'private, no-store, max-age=0')
        self.assertEqual(private_image['X-Content-Type-Options'], 'nosniff')
        self.assertTrue(b''.join(private_image.streaming_content))
        private_image.close()

        history = self.client.get('/detect/list_detection_sessions/')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()[0]['session_id'], result['session_id'])

        detail = self.client.get(f'/detect/detection_session_details/{result["session_id"]}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['pest_name'], result['pest_name'])
        self.assertEqual(detail.json()['confidence'], result['confidence'])

        other_user = User.objects.create_user(
            username='other-live-detection-test',
            email='other-live-detection-test@example.com',
            password='test-password',
        )
        self.client.force_login(other_user)
        other_detail = self.client.get(f'/detect/detection_session_details/{result["session_id"]}/')
        self.assertEqual(other_detail.status_code, 404)
        self.assertEqual(self.client.get('/detect/list_detection_sessions/').json(), [])
        self.assertEqual(self.client.get(result['user_image_url']).status_code, 404)
        self.assertTrue(PestDetection.objects.filter(id=result['session_id']).exists())
