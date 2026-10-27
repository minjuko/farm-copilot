import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.db import DatabaseError
from django.test import SimpleTestCase, TestCase

from detect.artifact import (
    _ARTIFACT_CHECK_CACHE,
    EXPECTED_CLASSES,
    EXPECTED_SHA256,
    EXPECTED_SIZE,
    ModelContractMismatchError,
    ModelLoadFailedError,
    RuntimeUnavailableError,
    check_artifact_readiness,
)
from detect.models import Pest, PestDetection, PestModelClass


class ModelManifestTests(SimpleTestCase):
    def test_manifest_matches_runtime_artifact_contract(self):
        manifest_path = Path(__file__).resolve().parents[1] / 'model_manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

        self.assertEqual(manifest['size_bytes'], EXPECTED_SIZE)
        self.assertEqual(manifest['sha256'], EXPECTED_SHA256)
        self.assertEqual(manifest['task'], 'detect')
        self.assertEqual(manifest['class_count'], len(EXPECTED_CLASSES))
        self.assertEqual(
            {int(class_id): name for class_id, name in manifest['classes'].items()},
            EXPECTED_CLASSES,
        )
        self.assertEqual(manifest['filename'], 'best.pt')


class ModelPreflightCommandTests(SimpleTestCase):
    def test_missing_artifact_has_actionable_failure(self):
        with self.assertRaisesMessage(CommandError, 'Model file is missing'):
            call_command('check_detection_model', model_path='missing-best.pt')

    def test_hash_mismatch_is_rejected_without_loading_model(self):
        with tempfile.NamedTemporaryFile() as artifact:
            with patch(
                'detect.management.commands.check_detection_model.sha256_file', return_value='bad'
            ):
                with patch(
                    'detect.management.commands.check_detection_model.load_validated_model'
                ) as load:
                    with self.assertRaisesMessage(CommandError, 'integrity mismatch'):
                        call_command('check_detection_model', model_path=artifact.name)
            load.assert_not_called()

    def test_cpu_smoke_test_is_run_after_integrity_and_contract_checks(self):
        class FakeModel:
            def __call__(self, *_args, **kwargs):
                self.kwargs = kwargs

        model = FakeModel()
        with tempfile.NamedTemporaryFile() as artifact:
            with patch(
                'detect.management.commands.check_detection_model.sha256_file',
                return_value=EXPECTED_SHA256,
            ):
                with patch(
                    'detect.management.commands.check_detection_model.load_validated_model',
                    return_value=model,
                ):
                    with patch(
                        'detect.management.commands.check_detection_model.EXPECTED_SIZE',
                        Path(artifact.name).stat().st_size,
                    ):
                        call_command('check_detection_model', model_path=artifact.name)
        self.assertEqual(model.kwargs['device'], 'cpu')


class ArtifactReadinessCacheTests(SimpleTestCase):
    def setUp(self):
        _ARTIFACT_CHECK_CACHE.clear()

    def tearDown(self):
        _ARTIFACT_CHECK_CACHE.clear()
        from detect import views

        views._yolo_model = None

    def make_artifact(self):
        temp = tempfile.NamedTemporaryFile()
        self.addCleanup(temp.close)
        return Path(temp.name)

    def test_hash_mismatch_is_limited(self):
        path = self.make_artifact()
        with patch('detect.artifact.EXPECTED_SIZE', path.stat().st_size):
            with patch('detect.artifact.sha256_file', return_value='bad'):
                self.assertEqual(
                    check_artifact_readiness(path),
                    {'ready': False, 'reason': 'model_integrity_mismatch'},
                )

    def test_runtime_load_and_contract_failures_are_distinguished(self):
        path = self.make_artifact()
        with patch('detect.artifact.EXPECTED_SIZE', path.stat().st_size):
            with patch('detect.artifact.sha256_file', return_value=EXPECTED_SHA256):
                for error, reason in (
                    (RuntimeUnavailableError(), 'runtime_unavailable'),
                    (ModelLoadFailedError(), 'model_load_failed'),
                    (ModelContractMismatchError(), 'model_contract_mismatch'),
                ):
                    _ARTIFACT_CHECK_CACHE.clear()
                    with patch('detect.artifact.load_validated_model', side_effect=error):
                        self.assertEqual(
                            check_artifact_readiness(path), {'ready': False, 'reason': reason}
                        )

    def test_cpu_inference_failure_is_limited(self):
        path = self.make_artifact()

        class FailingModel:
            def __call__(self, *_args, **_kwargs):
                raise RuntimeError('smoke failed')

        with patch('detect.artifact.EXPECTED_SIZE', path.stat().st_size):
            with patch('detect.artifact.sha256_file', return_value=EXPECTED_SHA256):
                with patch('detect.artifact.load_validated_model', return_value=FailingModel()):
                    self.assertEqual(
                        check_artifact_readiness(path),
                        {'ready': False, 'reason': 'inference_unavailable'},
                    )

    def test_changed_artifact_fingerprint_reloads_cached_model(self):
        from detect import views

        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / 'model.pt'
        path.write_bytes(b'initial')

        class FakeModel:
            names = EXPECTED_CLASSES
            task = 'detect'
            model = SimpleNamespace(yaml={'nc': len(EXPECTED_CLASSES)})

            def __call__(self, *_args, **_kwargs):
                return []

        first_model = FakeModel()
        replacement_model = FakeModel()
        with patch('detect.artifact.EXPECTED_SIZE', path.stat().st_size):
            with patch('detect.artifact.sha256_file', return_value=EXPECTED_SHA256):
                with patch(
                    'detect.artifact.load_validated_model',
                    side_effect=[first_model, replacement_model],
                ) as load_model:
                    self.assertEqual(
                        check_artifact_readiness(path), {'ready': True, 'reason': None}
                    )
                    self.assertIs(views._yolo_model, first_model)

                    path.write_bytes(b'replaced artifact')
                    import detect.artifact as artifact

                    artifact.EXPECTED_SIZE = path.stat().st_size
                    self.assertEqual(
                        check_artifact_readiness(path), {'ready': True, 'reason': None}
                    )

        self.assertIs(views._yolo_model, replacement_model)
        self.assertEqual(load_model.call_count, 2)


class DetectionCatalogSeedTests(TestCase):
    def test_seed_creates_catalog_and_repeats_without_duplicates(self):
        call_command('seed_detection_catalog', verbosity=0)
        self.assertEqual(Pest.objects.count(), 5)
        self.assertEqual(PestModelClass.objects.count(), 6)
        call_command('seed_detection_catalog', verbosity=0)
        self.assertEqual(Pest.objects.count(), 5)
        self.assertEqual(PestModelClass.objects.count(), 6)
        mappings = {row.class_id: row for row in PestModelClass.objects.select_related('pest')}
        self.assertEqual(set(mappings), set(range(6)))
        self.assertEqual(mappings[2].pest.code, 'CUCUMBER_DOWNY_MILDEW')
        self.assertEqual(mappings[4].pest_id, mappings[2].pest_id)
        for mapping in mappings.values():
            self.assertTrue(mapping.pest.occurrence_environment)
            self.assertTrue(mapping.pest.symptom_description)
            self.assertTrue(mapping.pest.prevention_methods)
            self.assertTrue(mapping.pest.pesticide_name)
            self.assertTrue(mapping.pest.information_source)
            self.assertTrue(mapping.pest.information_source_url)

    def test_seed_preserves_user_and_detection_records(self):
        from accounts.models import User

        user = User.objects.create_user(
            username='catalog-preserve',
            email='catalog-preserve@example.com',
            password='test-password',
        )
        unrelated = Pest.objects.create(code='UNRELATED', pest_name='Unrelated')
        PestDetection.objects.create(user=user, pest=unrelated, confidence=71.0)
        before_users = User.objects.count()
        call_command('seed_detection_catalog', verbosity=0)
        self.assertEqual(User.objects.count(), before_users)
        self.assertTrue(Pest.objects.filter(pk=unrelated.pk).exists())
        self.assertEqual(PestDetection.objects.filter(user=user).count(), 1)

    def test_conflicting_class_mapping_fails_before_any_catalog_write(self):
        conflicting_pest = Pest.objects.create(code='OTHER', pest_name='Other')
        PestModelClass.objects.create(class_id=2, model_label='Other', pest=conflicting_pest)
        with self.assertRaisesMessage(CommandError, 'no changes were made'):
            call_command('seed_detection_catalog', verbosity=0)
        self.assertEqual(Pest.objects.count(), 1)
        self.assertEqual(PestModelClass.objects.count(), 1)

    def test_transaction_rolls_back_partial_seed(self):
        with patch(
            'detect.management.commands.seed_detection_catalog.PestModelClass.objects.create',
            side_effect=RuntimeError('test failure'),
        ):
            with self.assertRaises(RuntimeError):
                call_command('seed_detection_catalog', verbosity=0)
        self.assertEqual(Pest.objects.count(), 0)
        self.assertEqual(PestModelClass.objects.count(), 0)


class DetectionReadinessTests(TestCase):
    @patch(
        'common.views.check_artifact_readiness',
        return_value={'ready': False, 'reason': 'runtime_unavailable'},
    )
    def test_artifact_failure_is_unavailable_without_database_lookup(self, _artifact):
        from common.views import _detection_readiness

        with patch('common.views.PestModelClass.objects') as mappings:
            self.assertEqual(_detection_readiness(), (False, 'runtime_unavailable'))
            mappings.select_related.assert_not_called()

    @patch('common.views.check_artifact_readiness', return_value={'ready': True, 'reason': None})
    def test_missing_mapping_is_limited(self, _artifact):
        from common.views import _detection_readiness

        self.assertEqual(_detection_readiness(), (False, 'catalog_incomplete'))

    @patch('common.views.check_artifact_readiness', return_value={'ready': True, 'reason': None})
    def test_seeded_catalog_and_artifact_report_ready(self, _artifact):
        from common.views import _detection_readiness

        self.assertEqual(_detection_readiness(), (False, 'catalog_incomplete'))
        call_command('seed_detection_catalog', verbosity=0)
        self.assertEqual(_detection_readiness(), (True, None))

    @patch('common.views.check_artifact_readiness', return_value={'ready': True, 'reason': None})
    def test_database_error_is_distinguished(self, _artifact):
        from common.views import _detection_readiness

        with patch(
            'common.views.PestModelClass.objects.select_related', side_effect=DatabaseError('no db')
        ):
            self.assertEqual(_detection_readiness(), (False, 'database_unavailable'))
