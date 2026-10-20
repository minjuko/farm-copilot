import copy
import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from evaluation import evaluate as ev

EXAMPLE = Path(ev.__file__).with_name('evaluation_config.example.json')


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'private-data'
        self.root.mkdir()
        self.model = self.base / 'model.pt'
        self.model.write_bytes(b'synthetic mock model, not a checkpoint')
        self.manifest = self.base / 'manifest.csv'
        self.output = self.base / 'results'
        self.config = ev.load_config(EXAMPLE)
        self.rows = []
        self.add_row()
        self.save_manifest()
        self.predictor = Mock()
        self.predictor.names = {item['id']: item['name'] for item in self.config['class_contract']}
        self.predictor.runtime = {'kind': 'mock'}
        self.predictor.predict.return_value = [{'class_id': 0, 'confidence': 0.8}]
        self.factory = Mock(return_value=self.predictor)

    def add_row(self, **changes):
        index = len(self.rows)
        path = self.root / f'image-{index}.png'
        Image.new('RGB', (8, 8), color=(index, 40, 70)).save(path)
        row = dict(
            zip(
                ev.FIELDS,
                [
                    f'image-{index}',
                    path.name,
                    ev.sha256(path),
                    'validation',
                    f'plant-{index}',
                    f'original-{index}',
                    'supported',
                    'disease',
                    'pepper',
                    'PEPPER_ANTHRACNOSE',
                    'verified',
                    'synthetic-unit-test-only',
                    'synthetic',
                    'v1',
                    'test-only',
                    'approved',
                    'unknown',
                ],
            )
        )
        row.update(changes)
        self.rows.append(row)
        return row

    def save_manifest(self):
        with self.manifest.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=ev.FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)

    def run_tool(self, **kwargs):
        return ev.run(
            self.config,
            self.model,
            self.manifest,
            self.root,
            self.output,
            predictor_factory=self.factory,
            **kwargs,
        )

    def assert_manifest_blocked(self, message):
        self.save_manifest()
        with self.assertRaisesRegex(ev.EvaluationError, message):
            self.run_tool()
        self.factory.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_configuration_can_be_checked_without_data_or_model(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ev.main(['--config', str(EXAMPLE), '--check-config']), 0)

    def test_invalid_config_fields_ranges_and_types(self):
        cases = [
            ('confidence_threshold', -0.1),
            ('confidence_threshold', 1.1),
            ('confidence_threshold', float('nan')),
            ('confidence_threshold', True),
            ('prediction_confidence_floor', 0.9),
            ('nms_iou', float('inf')),
            ('tta', 'true'),
            ('imgsz', 641),
            ('seed', -1),
            ('device', 'auto'),
            ('mode', 'bbox'),
            ('class_semantics', 'assumed'),
            ('max_det', 0),
        ]
        path = self.base / 'config.json'
        for key, value in cases:
            with self.subTest(key=key, value=value):
                config = copy.deepcopy(self.config)
                config[key] = value
                path.write_text(json.dumps(config), encoding='utf-8')
                with self.assertRaises(ev.EvaluationError):
                    ev.load_config(path)

    def test_config_rejects_duplicate_json_keys_and_unknown_fields(self):
        path = self.base / 'config.json'
        for payload in ('{"mode":"image","mode":"image"}', '{"api_key":"not-real"}'):
            path.write_text(payload, encoding='utf-8')
            with self.assertRaises(ev.EvaluationError):
                ev.load_config(path)

    def test_config_rejects_duplicate_class_ids_and_unknown_labels(self):
        path = self.base / 'config.json'
        for key, value in [('id', 4), ('id', True), ('service_label', 'invented')]:
            config = copy.deepcopy(self.config)
            config['class_contract'][0][key] = value
            path.write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
            with self.assertRaises(ev.EvaluationError):
                ev.load_config(path)

    def test_missing_model_is_blocked_before_runtime(self):
        self.model = self.base / 'missing.pt'
        with self.assertRaisesRegex(ev.EvaluationError, 'existing local'):
            self.run_tool()
        self.factory.assert_not_called()

    def test_missing_image_is_blocked(self):
        self.rows[0]['relative_path'] = 'missing.png'
        self.assert_manifest_blocked('image missing')

    def test_empty_manifest_and_empty_split_are_blocked(self):
        self.rows.clear()
        self.assert_manifest_blocked('Manifest is empty')
        self.add_row(split='test')
        self.assert_manifest_blocked('Selected split is empty')

    def test_wrong_header_and_row_width_are_blocked(self):
        for payload in ('image_id,path\na,b\n', ','.join(ev.FIELDS) + '\na,b\n'):
            self.manifest.write_text(payload, encoding='utf-8')
            with self.assertRaises(ev.EvaluationError):
                self.run_tool()

    def test_bad_image_content_and_hash_are_blocked(self):
        image_path = self.root / self.rows[0]['relative_path']
        image_path.write_bytes(b'not an image')
        self.assert_manifest_blocked('SHA-256 mismatch')
        self.rows[0]['sha256'] = ev.sha256(image_path)
        self.assert_manifest_blocked('Invalid or unsafe')

    def test_path_traversal_and_absolute_paths_are_blocked(self):
        for value in ('../outside.png', '/private.png', 'C:/private.png', '..\\private.png'):
            self.rows[0]['relative_path'] = value
            self.assert_manifest_blocked('safe relative')

    def test_hash_duplicates_are_rejected_even_with_other_ids(self):
        self.add_row(relative_path=self.rows[0]['relative_path'], sha256=self.rows[0]['sha256'])
        self.assert_manifest_blocked('duplicate image content')

    def test_group_and_original_cannot_cross_splits(self):
        for field in ('group_id', 'origin_id'):
            with self.subTest(field=field):
                self.rows = self.rows[:1]
                self.add_row(split='test', **{field: self.rows[0][field]})
                self.assert_manifest_blocked('crosses splits')

    def test_missing_ground_truth_and_unreviewed_records_block_scoring(self):
        for field, value in [
            ('target_labels', ''),
            ('review_status', 'unreviewed'),
            ('label_evidence', ''),
        ]:
            original = self.rows[0][field]
            self.rows[0][field] = value
            self.assert_manifest_blocked('verified ground truth required')
            self.rows[0][field] = original

    def test_pending_license_and_known_training_overlap_block_execution(self):
        for field, value, message in [
            ('license_review', 'pending', 'usage review pending'),
            ('training_overlap', 'overlap', 'known training overlap'),
        ]:
            original = self.rows[0][field]
            self.rows[0][field] = value
            self.assert_manifest_blocked(message)
            self.rows[0][field] = original

    def test_label_category_and_crop_contradictions_are_blocked(self):
        for changes in (
            {'target_labels': 'UNKNOWN'},
            {'target_labels': 'healthy'},
            {'crop': 'tomato'},
            {'category': 'normal', 'subcategory': 'healthy'},
        ):
            original = dict(self.rows[0])
            self.rows[0].update(changes)
            self.assert_manifest_blocked('invalid target|supported needs|disagree')
            self.rows[0] = original

    def test_preflight_never_loads_ai_and_does_not_write_results(self):
        result = self.run_tool(validate_only=True)
        self.assertEqual(result['status'], 'input_validation_only')
        self.assertIsNone(result['metrics'])
        self.factory.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_invalid_model_names_are_rejected(self):
        self.predictor.names = {0: 'wrong'}
        with self.assertRaisesRegex(ev.EvaluationError, 'names do not match'):
            self.run_tool()
        self.assertFalse(self.output.exists())

    def test_invalid_prediction_class_and_confidence_are_rejected(self):
        for class_id, conf in [
            (-1, 0.8),
            (6, 0.8),
            (1.5, 0.8),
            (True, 0.8),
            (float('nan'), 0.8),
            (0, -0.1),
            (0, 1.1),
            (0, float('inf')),
            (0, '0.8'),
            (0, True),
        ]:
            with self.subTest(class_id=class_id, conf=conf):
                with self.assertRaises(ev.EvaluationError):
                    ev.select_prediction([{'class_id': class_id, 'confidence': conf}], self.config)

    def test_threshold_inclusive_top1_and_duplicate_mapping(self):
        boxes, best = ev.select_prediction(
            [
                {'class_id': 0, 'confidence': 0.59},
                {'class_id': 4, 'confidence': 0.6},
                {'class_id': 2, 'confidence': 0.6},
            ],
            self.config,
        )
        self.assertEqual(best['class_id'], 4)
        self.assertEqual(boxes[1]['service_label'], boxes[2]['service_label'])
        self.assertIsNone(
            ev.select_prediction([{'class_id': 0, 'confidence': 0.599}], self.config)[1]
        )
        self.assertIsNone(ev.select_prediction([], self.config)[1])

    def test_predict_only_without_truth_never_emits_metrics(self):
        self.rows[0].update(target_labels='', review_status='unreviewed', label_evidence='')
        self.save_manifest()
        result = self.run_tool(score=False)
        self.assertIsNone(result['metrics'])
        self.assertEqual(result['status'], 'predictions_only')
        with self.assertRaises(ev.EvaluationError):
            ev.metrics(result['records'])

    def test_serialized_results_contain_truth_predictions_hashes_not_paths(self):
        original_model = self.model.read_bytes()
        result = self.run_tool()
        serialized = (self.output / 'report.json').read_text(encoding='utf-8')
        report = json.loads(serialized)
        self.assertNotIn(str(self.base), serialized)
        self.assertNotIn('relative_path', serialized)
        self.assertNotIn('private-data', serialized)
        self.assertEqual(report['records'][0]['target_labels'], ['PEPPER_ANTHRACNOSE'])
        self.assertEqual(report['records'][0]['predicted_class_id'], 0)
        self.assertEqual(report['model_sha256'], ev.sha256(self.model))
        self.assertEqual(report['manifest_sha256'], ev.sha256(self.manifest))
        self.assertEqual(self.model.read_bytes(), original_model)
        self.assertEqual(result['metrics']['supported_match_rate']['value'], 1)
        self.assertIsNone(result['metrics']['mAP'])
        self.assertIsNone(result['metrics']['raw_class_metrics'])
        with (self.output / 'predictions.csv').open(encoding='utf-8', newline='') as stream:
            records = list(csv.DictReader(stream))
        self.assertEqual(json.loads(records[0]['boxes'])[0]['class_id'], 0)

    def test_failures_do_not_create_success_report_or_leak_paths(self):
        self.predictor.predict.side_effect = RuntimeError(str(self.root / 'secret.png'))
        with self.assertRaisesRegex(ev.EvaluationError, 'no report was written') as error:
            self.run_tool()
        self.assertNotIn(str(self.root), str(error.exception))
        self.assertFalse(self.output.exists())

    def test_output_staging_failure_does_not_leave_partial_report_directory(self):
        with patch('evaluation.evaluate.csv.DictWriter', side_effect=OSError('private path')):
            with self.assertRaises(OSError):
                self.run_tool()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.base.glob('.evaluation-stage-*')), [])

    def test_existing_output_is_not_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / 'report.json'
        sentinel.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ev.EvaluationError, 'already exists'):
            self.run_tool()
        self.assertEqual(sentinel.read_text(encoding='utf-8'), 'keep')
        self.factory.assert_not_called()

    def test_metrics_use_explicit_denominators_and_keep_quality_separate(self):
        self.add_row(category='normal', subcategory='healthy', target_labels='healthy')
        self.add_row(category='unsupported', subcategory='disease', target_labels='unsupported')
        self.add_row(category='quality', subcategory='blur')
        self.add_row(target_labels='PEPPER_ANTHRACNOSE|PEPPER_POWDERY_MILDEW')
        self.save_manifest()
        self.predictor.predict.side_effect = [
            [{'class_id': 0, 'confidence': 0.9}],
            [{'class_id': 0, 'confidence': 0.8}],
            [],
            [{'class_id': 0, 'confidence': 0.9}],
            [{'class_id': 1, 'confidence': 0.8}],
        ]
        report = self.run_tool()['metrics']
        self.assertEqual(report['primary_count'], 3)
        self.assertEqual(report['accepted_error_rate']['value'], 0.5)
        self.assertEqual(report['abstention_rate']['value'], 1 / 3)
        self.assertEqual(report['negative_false_positive_rates']['normal']['value'], 1)
        self.assertEqual(report['negative_false_positive_rates']['unsupported']['value'], 0)
        self.assertEqual(
            report['per_service_label']['PEPPER_ANTHRACNOSE']['precision']['value'], 0.5
        )
        self.assertIsNone(report['per_service_label']['TOMATO_POWDERY_MILDEW']['recall']['value'])
        self.assertEqual(report['multilabel_diagnostic']['top1_in_truth_rate']['value'], 1)

    def test_quality_images_need_no_disease_truth_and_remain_separate(self):
        self.add_row(
            category='quality',
            subcategory='blur',
            target_labels='',
            review_status='unreviewed',
            label_evidence='',
        )
        self.save_manifest()
        self.predictor.predict.side_effect = [
            [{'class_id': 0, 'confidence': 0.9}],
            [],
        ]
        report = self.run_tool()['metrics']
        self.assertEqual(report['primary_count'], 1)
        self.assertEqual(report['category_diagnostics']['quality']['count'], 1)
        self.assertEqual(report['category_diagnostics']['quality']['abstention_rate']['value'], 1)

    def test_score_mode_still_requires_truth_for_every_non_quality_row(self):
        self.add_row(
            category='unsupported',
            subcategory='disease',
            target_labels='',
            review_status='unreviewed',
            label_evidence='',
        )
        self.assert_manifest_blocked('verified ground truth required')

    def test_all_abstentions_do_not_produce_zero_error_claim(self):
        self.predictor.predict.return_value = []
        report = self.run_tool()['metrics']
        self.assertIsNone(report['accepted_error_rate']['value'])
        self.assertEqual(report['supported_match_rate']['value'], 0)

    def test_model_modification_during_execution_is_detected(self):
        def change_model(*args):
            self.model.write_bytes(b'changed mock model')
            return []

        self.predictor.predict.side_effect = change_model
        with self.assertRaisesRegex(ev.EvaluationError, 'Model changed'):
            self.run_tool()
        self.assertFalse(self.output.exists())

    def test_cli_returns_nonzero_on_missing_files_without_private_path(self):
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = ev.main(['--config', str(self.base / 'private-name.json')])
        self.assertEqual(code, 2)
        self.assertNotIn('private-name', errors.getvalue())

    def test_yolo_adapter_forwards_explicit_settings_without_loading_real_model(self):
        fake_torch, fake_numpy = Mock(), Mock()
        fake_model = Mock(task='detect', names=self.predictor.names)
        fake_box = Mock()
        fake_box.cls.item.return_value = 4
        fake_box.conf.item.return_value = 0.75
        fake_model.predict.return_value = [SimpleNamespace(boxes=[fake_box])]
        fake_yolo = Mock(return_value=fake_model)
        with patch.dict(
            'sys.modules',
            {
                'torch': fake_torch,
                'numpy': fake_numpy,
                'ultralytics': SimpleNamespace(YOLO=fake_yolo),
            },
        ):
            adapter = ev.YoloPredictor(self.model, self.config)
            prediction = adapter.predict(self.root / 'image-0.png', self.config)
        self.assertEqual(prediction, [{'class_id': 4.0, 'confidence': 0.75}])
        args = fake_model.predict.call_args.kwargs
        self.assertEqual(args['conf'], 0.25)
        self.assertEqual(args['imgsz'], 640)
        self.assertTrue(args['augment'])
        self.assertEqual(args['device'], 'cpu')
        for flag in ('save', 'save_txt', 'save_crop', 'save_conf', 'show'):
            self.assertFalse(args[flag])
        fake_model.train.assert_not_called()

    def test_cli_empty_template_is_a_failure_not_an_evaluation(self):
        self.rows.clear()
        self.save_manifest()
        with redirect_stderr(io.StringIO()):
            code = ev.main(
                [
                    '--config',
                    str(EXAMPLE),
                    '--model',
                    str(self.model),
                    '--manifest',
                    str(self.manifest),
                    '--data-root',
                    str(self.root),
                    '--validate-only',
                ]
            )
        self.assertEqual(code, 2)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
