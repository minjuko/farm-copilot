import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import torch
from PIL import Image
from torch import nn

from model_training.benchmark_hardware import run_benchmark
from model_training.dataset import (
    CLASS_MAP,
    PepperClassificationDataset,
    load_class_map,
    load_manifest,
)
from model_training.metrics import classification_metrics
from model_training.split_manifest import split_manifest
from model_training.train_classifier import train


class TinyClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.linear = nn.Linear(3, 3)

    def forward(self, images):
        return self.linear(self.pool(images).flatten(1))


class TrainingPipelineTests(unittest.TestCase):
    def test_optional_two_class_contract_does_not_change_legacy_map(self):
        config = Path(__file__).resolve().parents[1] / 'aihub_2class_config.json'
        two_class = load_class_map(config)
        self.assertEqual(set(two_class), {0, 1})
        self.assertEqual(two_class[0]['name'], 'pepper_healthy')
        self.assertEqual(two_class[1]['disease'], 'a7')
        self.assertEqual(set(load_class_map()), {0, 1, 2})

    def test_dataset_transform_preserves_aspect_ratio_with_neutral_padding(self):
        dataset = PepperClassificationDataset([], self.data_root, image_size=32)
        tensor = dataset.transform(Image.new('RGB', (60, 30), (255, 0, 0)))
        self.assertEqual(tuple(tensor.shape), (3, 32, 32))
        self.assertLess(float(tensor[0, 0, 0]), 0.02)  # padded area is near normalized zero
        self.assertGreater(float(tensor[0, 16, 16]), 1.0)  # center retains image pixels

    def test_hardware_benchmark_schema_on_cpu(self):
        result = run_benchmark(
            device_name='cpu', batches=(2,), image_size=32, warmup=0, iterations=1
        )
        self.assertEqual(result['device'], 'cpu')
        self.assertFalse(result['pretrained_weights'])
        self.assertEqual(result['measurements'][0]['batch_size'], 2)
        self.assertGreater(result['measurements'][0]['images_per_second'], 0)
        self.assertIsNone(result['measurements'][0]['peak_cuda_memory_bytes'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data_root = self.root / 'data'
        self.data_root.mkdir()
        self.manifest = self.root / 'manifest.csv'
        self.output = self.root / 'run'
        self.rows = []
        fields = [
            'relative_path',
            'split',
            'class_id',
            'class_name',
            'crop',
            'task',
            'disease',
            'dataset_key',
            'dataset_version',
            'file_key',
            'source_sha256',
            'derived_sha256',
            'group_id',
            'group_evidence',
        ]
        for split_index, split in enumerate(('train', 'val', 'test')):
            for class_id, contract in CLASS_MAP.items():
                rel = f'{split}_{class_id}.jpg'
                path = self.data_root / rel
                image = Image.new('RGB', (20, 16))
                image.putdata(
                    [
                        (
                            (class_id * 60 + x * 3 + 20) % 256,
                            (split_index * 70 + y * 5) % 256,
                            (x * 7 + y * 11 + 80) % 256,
                        )
                        for y in range(16)
                        for x in range(20)
                    ]
                )
                image.save(path)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                self.rows.append(
                    {
                        'relative_path': rel,
                        'split': split,
                        'class_id': str(class_id),
                        'class_name': contract['name'],
                        'crop': contract['crop'],
                        'task': contract['task'],
                        'disease': contract['disease'],
                        'dataset_key': '525',
                        'dataset_version': 'test-v1',
                        'file_key': '51651',
                        'source_sha256': digest,
                        'derived_sha256': digest,
                        'group_id': f'group_{split}_{class_id}',
                        'group_evidence': 'verified synthetic fixture grouping',
                    }
                )
        with self.manifest.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.rows)

    def tearDown(self):
        self.temp.cleanup()

    def test_manifest_loader_and_split_contract(self):
        rows = load_manifest(self.manifest, self.data_root)
        dataset = PepperClassificationDataset(
            [row for row in rows if row['split'] == 'train'], self.data_root, image_size=32
        )
        image, label = dataset[0]
        self.assertEqual(tuple(image.shape), (3, 32, 32))
        self.assertIn(label, CLASS_MAP)

    def test_rejects_group_leakage_and_wrong_codes(self):
        self.rows[0]['group_id'] = self.rows[3]['group_id']
        with self.manifest.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=self.rows[0].keys())
            writer.writeheader()
            writer.writerows(self.rows)
        with self.assertRaisesRegex(ValueError, 'group_id crosses'):
            load_manifest(self.manifest, self.data_root)

    def test_single_class_unassigned_rows_cannot_enter_training(self):
        row = dict(self.rows[1])
        row['split'] = 'unassigned'
        with self.manifest.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
        with self.assertRaisesRegex(ValueError, 'invalid split'):
            load_manifest(self.manifest, self.data_root)

    def test_metrics_include_macro_f1_and_healthy_false_positive_rate(self):
        result = classification_metrics([0, 0, 1, 2], [0, 1, 1, 0], [0, 1, 2])
        self.assertEqual(result['n'], 4)
        self.assertEqual(result['normal_false_positive_rate'], 0.5)
        self.assertEqual(len(result['confusion_matrix']), 3)

    def test_group_split_is_reproducible_and_keeps_classes_in_all_splits(self):
        output = self.root / 'split.csv'
        result = split_manifest(self.manifest, output, seed=11)
        self.assertEqual(result['groups'], 9)
        rows = load_manifest(output, self.data_root)
        self.assertEqual({row['split'] for row in rows}, {'train', 'val', 'test'})
        for split in ('train', 'val', 'test'):
            self.assertEqual(
                {int(row['class_id']) for row in rows if row['split'] == split}, set(CLASS_MAP)
            )

    def test_cpu_training_smoke_checkpoint_reload_and_run_record(self):
        run = train(
            self.manifest,
            self.data_root,
            self.output,
            epochs=1,
            batch_size=3,
            image_size=32,
            pretrained=False,
            device_name='cpu',
            model_factory=TinyClassifier,
            architecture_name='tiny_test',
        )
        checkpoint = torch.load(
            self.output / 'best_model.pt', map_location='cpu', weights_only=True
        )
        reloaded = TinyClassifier()
        reloaded.load_state_dict(checkpoint['state_dict'])
        self.assertEqual(run['architecture'], 'tiny_test')
        self.assertEqual(run['test_metrics']['n'], 3)
        self.assertTrue((self.output / 'history.csv').is_file())
        with (self.output / 'test_predictions.csv').open(newline='', encoding='utf-8') as stream:
            self.assertEqual(len(list(csv.DictReader(stream))), 3)
        self.assertTrue((self.output / 'test_errors.csv').is_file())
        self.assertTrue(json.loads((self.output / 'run.json').read_text())['checkpoint'])


if __name__ == '__main__':
    unittest.main()
