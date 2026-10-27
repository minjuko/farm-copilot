import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from data_preparation.inspect_dataset import inspect_dataset


class InspectDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'images').mkdir()
        (self.root / 'labels').mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_sample(self, image_name='sample.JPG', **changes):
        Image.new('RGB', (100, 80)).save(self.root / 'images' / image_name, format='JPEG')
        ann = {
            'crop': 5,
            'disease': 'a7',
            'risk': 2,
            'grow': 13,
            'bbox': [{'x': 10, 'y': 15, 'w': 30, 'h': 20}],
            'part': [{'x': 12, 'y': 18, 'w': 10, 'h': 8, 'id': 0}],
        }
        ann.update(changes)
        payload = {
            'description': {'image': image_name, 'width': 100, 'height': 80, 'task': 1},
            'annotations': ann,
        }
        (self.root / 'labels' / (Path(image_name).stem + '.json')).write_text(
            json.dumps(payload), encoding='utf-8'
        )

    def test_reports_pairing_codes_and_boxes_without_mapping(self):
        self.write_sample()
        report = inspect_dataset(self.root)
        self.assertEqual(report['counts']['paired_json_to_image'], 1)
        self.assertEqual(report['source_code_distributions']['crop'], {'5': 1})
        self.assertEqual(report['source_code_distributions']['disease'], {'a7': 1})
        self.assertEqual(report['source_code_distributions']['task'], {'1': 1})
        self.assertEqual(report['bbox_count_per_json'], {'1': 1})
        self.assertEqual(report['part_count_per_json'], {'1': 1})
        self.assertEqual(report['boxes_outside_declared_image'], 0)
        self.assertFalse(report['interpretation']['source_files_modified'])
        self.assertIn('not performed', report['interpretation']['class_name_mapping'])

    def test_inspects_separate_image_and_label_roots_without_copying(self):
        self.write_sample()
        image_root = self.root / 'images'
        label_root = self.root / 'labels'

        report = inspect_dataset(image_root=image_root, label_root=label_root)

        self.assertEqual(report['counts']['images'], 1)
        self.assertEqual(report['counts']['json'], 1)
        self.assertEqual(report['counts']['paired_json_to_image'], 1)
        self.assertEqual(report['counts']['json_without_image'], 0)
        self.assertEqual(report['counts']['image_without_json_by_filename'], 0)
        self.assertEqual(report['image_root_name'], 'images')
        self.assertEqual(report['label_root_name'], 'labels')

    def test_requires_both_separate_roots(self):
        with self.assertRaisesRegex(ValueError, 'provided together'):
            inspect_dataset(image_root=self.root / 'images')

    def test_detects_invalid_and_out_of_bounds_annotations(self):
        self.write_sample(bbox=[{'x': 90, 'y': 70, 'w': 20, 'h': 20}])
        report = inspect_dataset(self.root)
        self.assertEqual(report['boxes_outside_declared_image'], 1)
        self.assertEqual(report['counts']['json_errors'], 0)

    def test_missing_image_and_bad_json_are_reported(self):
        self.write_sample()
        orphan = {
            'description': {'image': 'absent.jpg', 'width': 100, 'height': 80},
            'annotations': {'crop': 5, 'disease': 'a7', 'bbox': [], 'part': []},
        }
        (self.root / 'labels' / 'orphan.json').write_text(json.dumps(orphan), encoding='utf-8')
        (self.root / 'labels' / 'broken.json').write_text('{bad', encoding='utf-8')
        report = inspect_dataset(self.root)
        self.assertEqual(report['counts']['json_errors'], 1)
        self.assertEqual(report['counts']['json_without_image'], 1)

    def test_declared_image_size_must_match_decoded_file(self):
        self.write_sample()
        label = self.root / 'labels' / 'sample.json'
        payload = json.loads(label.read_text(encoding='utf-8'))
        payload['description']['width'] = 101
        label.write_text(json.dumps(payload), encoding='utf-8')
        report = inspect_dataset(self.root)
        self.assertEqual(report['image_size_mismatches'], 1)

    def test_hash_scan_detects_duplicate_image_bytes(self):
        self.write_sample()
        source = self.root / 'images' / 'sample.JPG'
        (self.root / 'images' / 'copy.jpg').write_bytes(source.read_bytes())
        report = inspect_dataset(self.root)
        self.assertEqual(report['sha256_duplicate_files'], 1)
        self.assertEqual(report['sha256_unique_images'], 1)

    def test_rejects_non_directory(self):
        with self.assertRaises(ValueError):
            inspect_dataset(self.root / 'absent')


if __name__ == '__main__':
    unittest.main()
