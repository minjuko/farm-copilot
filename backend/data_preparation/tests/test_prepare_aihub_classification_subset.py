import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from data_preparation.prepare_aihub_classification_subset import prepare_subset


class PrepareAihubClassificationSubsetTests(unittest.TestCase):
    def test_extracts_only_seeded_label_matched_images_and_records_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'classes.json'
            config.write_text(json.dumps({
                'dataset_key': '525', 'classes': [
                    {'class_id': 0, 'name': 'pepper_healthy', 'crop': '5', 'task': '0', 'disease': '00'},
                    {'class_id': 1, 'name': 'pepper_anthracnose', 'crop': '5', 'task': '1', 'disease': 'a7'},
                ],
            }), encoding='utf-8')
            inputs = {}
            for class_name, codes in (
                    ('pepper_healthy', ('5', '0', '00')),
                    ('pepper_anthracnose', ('5', '1', 'a7')),
                ):
                    archive_path = root / f'{class_name}.zip'
                    csv_path = root / f'{class_name}.csv'
                    rows = []
                    with zipfile.ZipFile(archive_path, 'w') as archive:
                        for index in range(3):
                            ref = f'{class_name}_{index}.jpg'
                            buffer = root / ref
                            class_offset = 0 if class_name == 'pepper_healthy' else 100
                            Image.new('RGB', (30, 20), (class_offset + index * 30, 60, 90)).save(buffer)
                            archive.write(buffer, ref)
                            rows.append({'image_ref': ref, 'crop': codes[0], 'task': codes[1], 'disease': codes[2], 'date': '20261020'})
                    with csv_path.open('w', newline='', encoding='utf-8') as stream:
                        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
                    inputs[class_name] = (archive_path, csv_path)
            output = root / 'subset'
            result = prepare_subset(inputs, config, output, sample_size=2, seed=9)
            self.assertEqual(result['class_counts'], {'pepper_healthy': 2, 'pepper_anthracnose': 2})
            with (output / 'manifest.csv').open(newline='', encoding='utf-8-sig') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(row['split'] == 'unassigned' and not row['group_id'] for row in rows))
            self.assertTrue(all(len(row['source_sha256']) == 64 and len(row['derived_sha256']) == 64 for row in rows))
            self.assertEqual(len(list((output / 'images').rglob('*.jpg'))), 4)

    def test_refuses_ambiguous_member_basename(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'classes.json'
            config.write_text(json.dumps({'classes': [
                {'class_id': 0, 'name': 'pepper_healthy', 'crop': '5', 'task': '0', 'disease': '00'},
                {'class_id': 1, 'name': 'pepper_anthracnose', 'crop': '5', 'task': '1', 'disease': 'a7'},
            ]}), encoding='utf-8')
            inputs = {}
            for name, codes in (('pepper_healthy', ('5', '0', '00')), ('pepper_anthracnose', ('5', '1', 'a7'))):
                archive = root / f'{name}.zip'
                with zipfile.ZipFile(archive, 'w') as zf:
                    zf.writestr('a/shared.jpg', b'x')
                    zf.writestr('b/shared.jpg', b'x')
                path = root / f'{name}.csv'
                with path.open('w', newline='', encoding='utf-8') as stream:
                    writer = csv.DictWriter(stream, fieldnames=['image_ref', 'crop', 'task', 'disease'])
                    writer.writeheader()
                    writer.writerow({'image_ref': f'{name}/shared.jpg', 'crop': codes[0], 'task': codes[1], 'disease': codes[2]})
                inputs[name] = (archive, path)
            with self.assertRaisesRegex(ValueError, 'ambiguous ZIP basename'):
                prepare_subset(inputs, config, root / 'out', sample_size=1)
