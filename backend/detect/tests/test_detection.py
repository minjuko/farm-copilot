import os
import tempfile
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from PIL import Image

from common.exceptions import ServiceUnavailableError, ValidationError

from .. import views
from ..models import Pest, PestModelClass


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

        with self.assertLogs('detect.views', level='WARNING'):
            with self.assertRaises(ServiceUnavailableError) as context:
                views.get_yolo_model()

        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn('corrupt model', context.exception.message)

    def test_model_class_contract_accepts_expected_metadata(self):
        model = SimpleNamespace(names=views.EXPECTED_MODEL_CLASS_NAMES.copy())
        views.validate_model_contract(model)

    def test_model_class_contract_rejects_another_artifact(self):
        model = SimpleNamespace(names={0: 'different class'})
        with self.assertRaises(ServiceUnavailableError) as context:
            views.validate_model_contract(model)
        self.assertEqual(
            context.exception.message,
            views.MODEL_CONTRACT_MISMATCH_MESSAGE,
        )

    def test_model_path_relative_environment_value_is_based_on_base_dir(self):
        with patch.dict(os.environ, {'YOLO_MODEL_PATH': 'artifacts/best.pt'}):
            self.assertEqual(
                views.resolve_model_path(),
                views.DEFAULT_MODEL_PATH.parent / 'artifacts' / 'best.pt',
            )

    def test_image_validation_rejects_invalid_and_empty_files(self):
        invalid = SimpleUploadedFile('crop.jpg', b'not-an-image', content_type='image/jpeg')
        empty = SimpleUploadedFile('crop.jpg', b'', content_type='image/jpeg')

        with self.assertRaises(ValidationError):
            views.validate_image_file(invalid)
        with self.assertRaises(ValidationError):
            views.validate_image_file(empty)

    @patch.object(views.PestModelClass.objects, 'select_related')
    def test_unconfigured_model_classes_are_blocked(self, select_related):
        select_related.return_value.get.side_effect = PestModelClass.DoesNotExist
        for class_id in (0, 3, 4):
            with self.subTest(class_id=class_id):
                with self.assertRaises(ServiceUnavailableError) as context:
                    views.map_model_class_to_pest_id(class_id)
                self.assertEqual(context.exception.status_code, 503)
                self.assertEqual(
                    context.exception.message,
                    views.MAPPING_UNAVAILABLE_MESSAGE,
                )

    @patch.object(views, 'Pest')
    @patch.object(views, 'process_image')
    def test_unresolved_mapping_does_not_lookup_or_save_pest(self, process_image, pest_model):
        process_image.side_effect = ServiceUnavailableError(views.MAPPING_UNAVAILABLE_MESSAGE)

        with self.assertRaises(ServiceUnavailableError) as context:
            views.upload_image_for_detection(self.make_request(self.make_image('JPEG')))

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.message, views.MAPPING_UNAVAILABLE_MESSAGE)
        pest_model.objects.get.assert_not_called()

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
        model.assert_called_once_with(
            image_path,
            augment=True,
            verbose=False,
        )

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


class DetectionModelClassMappingTests(TestCase):
    def test_explicit_zero_based_mapping_resolves_the_pest(self):
        pest = Pest.objects.create(
            code='PEPPER_ANTHRACNOSE',
            pest_name='고추 탄저병',
        )
        PestModelClass.objects.create(
            class_id=0,
            model_label='고추 탄저병',
            pest=pest,
        )

        self.assertEqual(views.map_model_class_to_pest_id(0), pest.id)

    def test_multiple_model_classes_can_resolve_the_same_pest(self):
        pest = Pest.objects.create(
            code='CUCUMBER_DOWNY_MILDEW',
            pest_name='오이 노균병',
        )
        PestModelClass.objects.create(class_id=2, model_label='오이 노균병', pest=pest)
        PestModelClass.objects.create(class_id=4, model_label='오이 노균병', pest=pest)

        self.assertEqual(views.map_model_class_to_pest_id(2), pest.id)
        self.assertEqual(views.map_model_class_to_pest_id(4), pest.id)

    @patch.object(views, 'import_module')
    @patch.object(views, 'get_yolo_model')
    def test_process_image_returns_highest_confidence_mapped_pest(self, get_model, import_module):
        lower_pest = Pest.objects.create(code='LOWER', pest_name='낮은 신뢰도 병해')
        higher_pest = Pest.objects.create(code='HIGHER', pest_name='높은 신뢰도 병해')
        PestModelClass.objects.create(class_id=0, model_label='lower', pest=lower_pest)
        PestModelClass.objects.create(class_id=1, model_label='higher', pest=higher_pest)

        lower_box = Mock()
        lower_box.conf.item.return_value = 0.7
        lower_box.cls.item.return_value = 0
        higher_box = Mock()
        higher_box.conf.item.return_value = 0.95
        higher_box.cls.item.return_value = 1
        result = Mock(boxes=[lower_box, higher_box])
        result.plot.return_value = object()
        get_model.return_value = Mock(return_value=[result])
        import_module.return_value.imencode.return_value = (
            True,
            np.array([1, 2, 3], dtype=np.uint8),
        )

        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            image_file.write(b'image')
            image_file.flush()
            pest_id, confidence, content = views.process_image(image_file.name)

        self.assertEqual(pest_id, higher_pest.id)
        self.assertEqual(confidence, 95.0)
        self.assertEqual(content.read(), bytes([1, 2, 3]))


class DetectionFixtureContractTests(TestCase):
    fixtures = ['model_classes.json']

    def test_fixture_covers_every_model_class_with_verified_details(self):
        mappings = {
            mapping.class_id: mapping
            for mapping in PestModelClass.objects.select_related('pest').all()
        }
        self.assertEqual(
            {class_id: mapping.model_label for class_id, mapping in mappings.items()},
            views.EXPECTED_MODEL_CLASS_NAMES,
        )
        self.assertEqual(set(mappings), set(range(6)))
        for mapping in mappings.values():
            with self.subTest(class_id=mapping.class_id):
                self.assertTrue(mapping.pest.code)
                self.assertTrue(mapping.pest.occurrence_environment)
                self.assertTrue(mapping.pest.symptom_description)
                self.assertTrue(mapping.pest.prevention_methods)
                self.assertTrue(mapping.pest.information_source)
                self.assertTrue(mapping.pest.information_source_url.startswith('https://'))


class DetectCsrfBoundaryTests(TestCase):
    def setUp(self):
        from accounts.models import User

        self.user = User.objects.create_user(
            email='detect-csrf@example.com',
            username='detect-csrf',
            password='test-password',
        )
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def csrf_token(self):
        return self.client.get('/login/auth_check/').cookies['csrftoken'].value

    def test_detect_upload_requires_csrf(self):
        without_token = self.client.post(
            '/detect/upload/',
            data={'image': 'not-an-upload'},
        )
        self.assertEqual(without_token.status_code, 403)

        with_token = self.client.post(
            '/detect/upload/',
            data={'image': 'not-an-upload'},
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        self.assertEqual(with_token.status_code, 400)
