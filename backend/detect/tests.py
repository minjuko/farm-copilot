import os
import tempfile
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase
from PIL import Image

from aivle_big.exceptions import ServiceUnavailableError, ValidationError

from . import views


class DetectionRuntimeTests(SimpleTestCase):
    def setUp(self):
        views._yolo_model = None

    def tearDown(self):
        views._yolo_model = None

    def make_image(self, image_format='PNG', name=None):
        buffer = BytesIO()
        Image.new('RGB', (8, 8), color='green').save(buffer, format=image_format)
        extension = image_format.lower().replace('jpeg', 'jpg')
        return SimpleUploadedFile(
            name or f'crop.{extension}',
            buffer.getvalue(),
            content_type=f'image/{"jpeg" if image_format == "JPEG" else extension}',
        )

    def make_request(self, image_file):
        request = RequestFactory().post('/detect/upload/', {'image': image_file})
        request.user = SimpleNamespace(is_authenticated=True)
        return request

    def test_backend_root_template_renders(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    @patch.object(views, 'MODEL_PATH')
    def test_missing_model_is_isolated_to_detection_feature(self, model_path):
        model_path.exists.return_value = False

        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_yolo_model()

        self.assertEqual(context.exception.status_code, 503)

    @patch.object(views, 'MODEL_PATH')
    @patch.object(views, 'import_module')
    def test_model_initialization_failure_is_controlled(self, import_module, model_path):
        model_path.exists.return_value = True
        import_module.return_value.YOLO.side_effect = ValueError('corrupt model')

        with self.assertRaises(ServiceUnavailableError) as context:
            views.get_yolo_model()

        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn('corrupt model', context.exception.message)

    def test_model_path_relative_environment_value_is_based_on_base_dir(self):
        with patch.dict(os.environ, {'YOLO_MODEL_PATH': 'artifacts/best.pt'}):
            self.assertEqual(
                views.resolve_model_path(),
                views.DEFAULT_MODEL_PATH.parent / 'artifacts' / 'best.pt',
            )

    def test_image_validation_rejects_invalid_and_empty_files(self):
        invalid = SimpleUploadedFile(
            'crop.jpg', b'not-an-image', content_type='image/jpeg'
        )
        empty = SimpleUploadedFile('crop.jpg', b'', content_type='image/jpeg')

        with self.assertRaises(ValidationError):
            views.validate_image_file(invalid)
        with self.assertRaises(ValidationError):
            views.validate_image_file(empty)

    def test_model_class_mapping_is_zero_based(self):
        self.assertEqual(views.map_model_class_to_pest_id(0), 1)
        self.assertEqual(views.map_model_class_to_pest_id(12), 13)

    def test_negative_or_malformed_class_is_rejected(self):
        with self.assertRaises(ValidationError):
            views.map_model_class_to_pest_id(-1)
        with self.assertRaises(ValidationError):
            views.map_model_class_to_pest_id('unknown')

    @patch.object(views, 'Pest')
    @patch.object(views, 'process_image')
    def test_unknown_class_does_not_fallback_to_another_pest(
        self, process_image, pest_model
    ):
        process_image.return_value = (99, 90.0, ContentFile(b'image', name='crop.jpg'))
        pest_model.DoesNotExist = type('DoesNotExist', (Exception,), {})
        pest_model.objects.get.side_effect = pest_model.DoesNotExist

        with self.assertRaises(ValidationError) as context:
            views.upload_image_for_detection(self.make_request(self.make_image('JPEG')))

        self.assertIn('not registered', context.exception.message)
        pest_model.objects.get.assert_called_once_with(id=99)

    @patch.object(views, 'get_yolo_model')
    def test_empty_detection_returns_no_pest_without_fake_fallback(self, get_model):
        box_result = SimpleNamespace(boxes=[])
        model = Mock(return_value=[box_result])
        get_model.return_value = model
        image_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        try:
            image_file.write(b'image')
            image_file.flush()
            image_path = image_file.name
            image_file.close()
            pest_id, confidence, content = views.process_image(image_path)
        finally:
            if not image_file.closed:
                image_file.close()
            os.remove(image_path)

        self.assertIsNone(pest_id)
        self.assertEqual(confidence, 0.0)
        self.assertEqual(content.read(), b'image')

    @patch.object(views, 'import_module')
    @patch.object(views, 'get_yolo_model')
    def test_annotation_encode_failure_is_controlled(self, get_model, import_module):
        box = Mock()
        box.conf.item.return_value = 0.9
        box.cls.item.return_value = 0
        result = Mock(boxes=[box])
        result.plot.return_value = object()
        get_model.return_value = Mock(return_value=[result])
        import_module.return_value.imencode.return_value = (False, None)

        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            image_file.write(b'image')
            image_file.flush()
            with self.assertRaises(ServiceUnavailableError) as context:
                views.process_image(image_file.name)

        self.assertNotIn('buffer', context.exception.message)

    @patch.object(views, 'process_image')
    def test_temp_image_is_removed_when_inference_fails(self, process_image):
        captured_path = []

        def fail(path):
            captured_path.append(path)
            raise ServiceUnavailableError('runtime unavailable')

        process_image.side_effect = fail
        with self.assertRaises(ServiceUnavailableError):
            views.upload_image_for_detection(self.make_request(self.make_image('JPEG')))

        self.assertEqual(len(captured_path), 1)
        self.assertFalse(os.path.exists(captured_path[0]))
