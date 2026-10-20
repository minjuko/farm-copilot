import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from data_preparation.inspect_archive_sample import _extension_matches, inspect_archive_sample, main


class InspectArchiveSampleTests(unittest.TestCase):
    def test_jpeg_extension_accepts_pillow_mpo_container(self):
        self.assertTrue(_extension_matches('jpg', 'MPO'))
        self.assertTrue(_extension_matches('jpeg', 'JPEG'))
        self.assertFalse(_extension_matches('png', 'JPEG'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.labels = self.root / 'labels'
        self.labels.mkdir()
        self.archive_path = self.root / 'images.zip'

    def tearDown(self):
        self.temp.cleanup()

    def write_image(self, color, name=None):
        path = self.root / (name or f'{color[0]}-{color[1]}-{color[2]}.jpg')
        Image.new('RGB', (24, 16), color).save(path, format='JPEG')
        return path.read_bytes()

    def write_label(
        self, filename, image_ref, *, risk=2, grow=13, area=1, width=24, height=16, disease='a7'
    ):
        data = {
            'description': {
                'image': image_ref,
                'task': 1,
                'date': '20210802',
                'time': '1401',
                'width': width,
                'height': height,
            },
            'annotations': {
                'crop': 5,
                'disease': disease,
                'risk': risk,
                'grow': grow,
                'area': area,
                'bbox': [],
                'part': [],
            },
        }
        (self.labels / filename).write_text(json.dumps(data), encoding='utf-8')

    def write_zip(self, members):
        with zipfile.ZipFile(self.archive_path, 'w', compression=zipfile.ZIP_STORED) as archive:
            for name, content in members:
                archive.writestr(name, content)

    def test_pairs_and_decodes_images_with_balanced_risk_sample(self):
        duplicate_bytes = self.write_image((30, 100, 30), 'first.jpg')
        different_bytes = self.write_image((220, 20, 20), 'second.jpg')
        members = []
        for index, risk in enumerate((2, 2, 3, 3)):
            image_ref = f'{100 + index}_20210802_5_1_a7_1_2_13_{risk}_{index}.JPG'
            self.write_label(f'{index}.json', image_ref, risk=risk)
            data = duplicate_bytes if index in (0, 1) else different_bytes
            members.append((f'고추/병해/{image_ref[:-4]}.jpg', data))
        self.write_zip(members)

        report = inspect_archive_sample(
            self.archive_path,
            self.labels,
            crop='5',
            task='1',
            disease='a7',
            sample_size=4,
            seed=44,
        )

        self.assertEqual(report['archive']['image_members'], 4)
        self.assertEqual(report['labels']['target_rows'], 4)
        self.assertEqual(report['labels']['paired_unique_refs'], 4)
        self.assertEqual(report['labels']['missing_refs'], 0)
        self.assertEqual(report['sample']['decoded_images'], 4)
        self.assertEqual(report['sample']['decode_errors'], [])
        self.assertEqual(report['sample']['risk_distribution'], {'2': 2, '3': 2})
        self.assertEqual(report['sample']['actual_format_distribution'], {'JPEG': 4})
        self.assertEqual(report['sample']['declared_dimension_mismatches'], 0)
        self.assertEqual(report['sample']['exact_duplicate_extras_in_sample'], 2)
        self.assertFalse((self.root / '고추').exists())

    def test_sampling_is_reproducible_and_keeps_each_risk_code(self):
        members = []
        for index, risk in enumerate((2, 2, 2, 3, 3, 3)):
            image_ref = f'{200 + index}_20210802_5_1_a7_1_2_13_{risk}_{index}.JPG'
            self.write_label(f'{index}.json', image_ref, risk=risk, area=index % 2)
            members.append((f'{image_ref[:-4]}.jpg', self.write_image((index * 20, 50, 90))))
        self.write_zip(members)

        kwargs = dict(crop='5', task='1', disease='a7', sample_size=4, seed=7)
        first = inspect_archive_sample(self.archive_path, self.labels, **kwargs)
        second = inspect_archive_sample(self.archive_path, self.labels, **kwargs)

        self.assertEqual(first['sample']['files'], second['sample']['files'])
        self.assertEqual(first['sample']['risk_distribution'], {'2': 2, '3': 2})

    def test_counts_missing_and_ambiguous_image_references(self):
        ref = '300_20210802_5_1_a7_1_2_13_2_0.JPG'
        self.write_label('one.json', ref)
        image = self.write_image((50, 60, 70))
        self.write_zip(
            [
                (f'first/{ref[:-4]}.jpg', image),
                (f'second/{ref[:-4]}.jpg', image),
            ]
        )

        report = inspect_archive_sample(
            self.archive_path,
            self.labels,
            crop='5',
            task='1',
            disease='a7',
            sample_size=1,
        )

        self.assertEqual(report['archive']['duplicate_image_basenames'], 1)
        self.assertEqual(report['labels']['ambiguous_refs'], 1)
        self.assertEqual(report['labels']['paired_unique_refs'], 0)

    def test_reports_corrupt_image_and_dimension_mismatch(self):
        ref = '400_20210802_5_1_a7_1_2_13_2_0.JPG'
        valid_ref = '401_20210803_5_1_a7_1_2_13_2_1.JPG'
        self.write_label('bad.json', ref, width=99)
        self.write_label('mismatch.json', valid_ref, width=99)
        self.write_zip(
            [
                (f'{ref[:-4]}.jpg', b'not an image'),
                (f'{valid_ref[:-4]}.jpg', self.write_image((80, 100, 30))),
            ]
        )

        report = inspect_archive_sample(
            self.archive_path,
            self.labels,
            crop='5',
            task='1',
            disease='a7',
            sample_size=2,
        )

        self.assertEqual(report['sample']['decoded_images'], 1)
        self.assertEqual(report['sample']['declared_dimension_mismatches'], 1)
        self.assertEqual(len(report['sample']['decode_errors']), 1)

    def test_cli_writes_private_report_and_refuses_overwrite(self):
        ref = '500_20210802_5_1_a7_1_2_13_2_0.JPG'
        self.write_label('one.json', ref)
        self.write_zip([(f'{ref[:-4]}.jpg', self.write_image((10, 30, 80)))])
        output = self.root / 'report.json'
        args = [
            '--archive',
            str(self.archive_path),
            '--label-root',
            str(self.labels),
            '--crop',
            '5',
            '--task',
            '1',
            '--disease',
            'a7',
            '--sample-size',
            '1',
            '--output',
            str(output),
        ]

        self.assertEqual(main(args), 0)
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['sample']['selected'], 1)
        self.assertEqual(main(args), 2)

    def test_rejects_nonpositive_sample_size(self):
        with self.assertRaises(ValueError):
            inspect_archive_sample(
                self.archive_path,
                self.labels,
                crop='5',
                task='1',
                disease='a7',
                sample_size=0,
            )


if __name__ == '__main__':
    unittest.main()
