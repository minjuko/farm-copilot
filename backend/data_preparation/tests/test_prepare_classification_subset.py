import csv
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from data_preparation.prepare_classification_subset import prepare_subset


class PrepareClassificationSubsetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive = self.root / 'ts1.zip'
        self.sample_report = self.root / 'sample.json'
        self.output = self.root / 'subset'
        self.rows = []
        with zipfile.ZipFile(self.archive, 'w', zipfile.ZIP_DEFLATED) as archive:
            for index in range(6):
                ref = f'{index}_20210802_5_1_a7_1_2_13_2_{index}.jpg'
                image_path = self.root / ref
                image = Image.new('RGB', (32, 20), (index * 20, 40, 80))
                exif = Image.Exif()
                exif[274] = 6 if index == 0 else 1
                image.save(image_path, format='JPEG', exif=exif)
                raw = image_path.read_bytes()
                archive.writestr(f'pepper/disease/{ref}', raw)
                self.rows.append(
                    {
                        'image_ref': ref,
                        'sha256': hashlib.sha256(raw).hexdigest(),
                        'date': '20210802',
                        'time': '1401',
                        'risk': index % 2 + 2,
                        'grow': 13,
                        'area': 1,
                    }
                )
        self.sample_report.write_text(
            json.dumps(
                {
                    'archive': {'size_bytes': self.archive.stat().st_size},
                    'labels': {
                        'target_codes': {'crop': '5', 'task': '1', 'disease': 'a7'},
                        'paired_unique_refs': 6,
                        'target_rows': 6,
                    },
                    'sample': {'files': self.rows},
                }
            ),
            encoding='utf-8',
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_prepares_seeded_exif_corrected_rgb_subset(self):
        report = prepare_subset(
            self.archive, self.sample_report, self.output, sample_size=6, seed=7
        )
        self.assertEqual(report['images_written'], 6)
        with (self.output / 'manifest.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 6)
        self.assertEqual({row['dataset_version'] for row in rows}, {'pepper-a7-tech-6-v1'})
        self.assertTrue(all(row['split'] == 'unassigned' for row in rows))
        self.assertTrue(all(row['group_id'] == '' for row in rows))
        for row in rows:
            with Image.open(self.output / row['relative_path']) as image:
                self.assertEqual(image.mode, 'RGB')
                self.assertEqual(image.format, 'JPEG')
                if row['source_image_ref'].startswith('0_'):
                    self.assertEqual(image.size, (20, 32))

    def test_rejects_existing_output_and_wrong_class_contract(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            prepare_subset(self.archive, self.sample_report, self.output, sample_size=2)
        self.output.rmdir()
        data = json.loads(self.sample_report.read_text(encoding='utf-8'))
        data['labels']['target_codes']['disease'] = 'a8'
        self.sample_report.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            prepare_subset(self.archive, self.sample_report, self.output, sample_size=2)


if __name__ == '__main__':
    unittest.main()
