import csv
import json
import tempfile
import unittest
from pathlib import Path

from data_preparation.export_label_manifest import export_manifest, main


class ExportLabelManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.labels = self.root / 'labels'
        self.labels.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_label(self, name, *, disease='a7', task=1, image=None):
        data = {
            'description': {
                'image': image or f'{name}.JPG',
                'task': task,
                'date': '20210802',
                'time': '1401',
                'width': 40,
                'height': 30,
            },
            'annotations': {
                'crop': 5,
                'disease': disease,
                'risk': 2,
                'grow': 13,
                'area': 1,
            },
        }
        (self.labels / f'{name}.json').write_text(json.dumps(data), encoding='utf-8')

    def test_exports_only_requested_class_metadata(self):
        self.write_label('anthracnose')
        self.write_label('powdery', disease='a8')
        self.write_label('healthy', disease='00', task=0)
        output = self.root / 'local' / 'labels.csv'

        result = export_manifest(self.labels, output, crop='5', task='1', disease='a7')

        self.assertEqual(result, {'json_files_seen': 3, 'target_rows': 1, 'error_count': 0})
        with output.open(newline='', encoding='utf-8-sig') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['disease'], 'a7')
        self.assertEqual(rows[0]['image_ref'], 'anthracnose.JPG')
        self.assertEqual(len(list(self.labels.glob('*.json'))), 3)

    def test_refuses_to_overwrite_existing_manifest(self):
        self.write_label('anthracnose')
        output = self.root / 'labels.csv'
        output.write_text('keep', encoding='utf-8')

        with self.assertRaises(FileExistsError):
            export_manifest(self.labels, output, crop='5', task='1', disease='a7')
        self.assertEqual(output.read_text(encoding='utf-8'), 'keep')

    def test_cli_handles_missing_root(self):
        output = self.root / 'manifest.csv'
        result = main(
            [
                '--label-root',
                str(self.root / 'missing'),
                '--output',
                str(output),
                '--crop',
                '5',
                '--task',
                '1',
                '--disease',
                'a7',
            ]
        )
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
