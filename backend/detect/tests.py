from unittest.mock import patch

from django.test import SimpleTestCase

from aivle_big.exceptions import ServiceUnavailableError
from . import views


class OptionalDetectionRuntimeTests(SimpleTestCase):
    def tearDown(self):
        views._yolo_model = None

    @patch.object(views, 'MODEL_PATH')
    def test_missing_model_is_isolated_to_detection_feature(self, model_path):
        model_path.exists.return_value = False

        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_yolo_model()

        self.assertEqual(context.exception.status_code, 503)
