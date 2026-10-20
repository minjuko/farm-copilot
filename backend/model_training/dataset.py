"""Strict CSV manifest validation and image loading for pepper classification."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision.transforms import Compose, Normalize, ToTensor

CLASS_MAP = {
    0: {'name': 'pepper_healthy', 'crop': '5', 'task': '0', 'disease': '00'},
    1: {'name': 'pepper_anthracnose', 'crop': '5', 'task': '1', 'disease': 'a7'},
    2: {'name': 'pepper_powdery_mildew', 'crop': '5', 'task': '1', 'disease': 'a8'},
}


def load_class_map(config_path: Path | None = None) -> dict[int, dict[str, str]]:
    """Load an optional class contract; the default preserves the legacy 3-class map."""
    if config_path is None:
        return CLASS_MAP
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    classes = config.get('classes') if isinstance(config, dict) else None
    if not isinstance(classes, list) or len(classes) < 2:
        raise ValueError('class config must contain at least two classes')
    result: dict[int, dict[str, str]] = {}
    for item in classes:
        if not isinstance(item, dict):
            raise ValueError('each class config entry must be an object')
        try:
            class_id = int(item['class_id'])
            contract = {key: str(item[key]) for key in ('name', 'crop', 'task', 'disease')}
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('invalid class config entry') from exc
        if class_id in result or not all(contract.values()):
            raise ValueError('class ids must be unique and class fields non-empty')
        result[class_id] = contract
    if sorted(result) != list(range(len(result))) or len({v['name'] for v in result.values()}) != len(result):
        raise ValueError('class ids must be contiguous and class names unique')
    return result
REQUIRED_FIELDS = {
    'relative_path',
    'split',
    'class_id',
    'class_name',
    'crop',
    'task',
    'disease',
    'source_sha256',
    'derived_sha256',
    'group_id',
    'group_evidence',
    'dataset_key',
    'dataset_version',
    'file_key',
}
SPLITS = {'train', 'val', 'test'}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(
    manifest_path: Path, data_root: Path,
    class_map: dict[int, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Read and validate paths, official label codes, hashes, and leakage groups."""
    class_map = class_map or CLASS_MAP
    manifest_path = manifest_path.resolve()
    data_root = data_root.resolve()
    if not manifest_path.is_file() or not data_root.is_dir():
        raise ValueError('manifest and dataset root must exist')
    with manifest_path.open('r', newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED_FIELDS.issubset(reader.fieldnames):
            raise ValueError('manifest is missing required columns')
        rows = list(reader)
    if not rows:
        raise ValueError('manifest is empty')

    seen_paths: set[str] = set()
    hash_splits: dict[str, set[str]] = defaultdict(set)
    group_splits: dict[str, set[str]] = defaultdict(set)
    for line, row in enumerate(rows, start=2):
        try:
            class_id = int(row['class_id'])
        except (TypeError, ValueError) as exc:
            raise ValueError(f'invalid class_id at manifest row {line}') from exc
        if class_id not in class_map:
            raise ValueError(f'unknown class_id at manifest row {line}')
        if (
            row['dataset_key'] != '525'
            or not row['dataset_version'].strip()
            or not row['file_key'].strip()
        ):
            raise ValueError(f'missing dataset provenance at manifest row {line}')
        expected = class_map[class_id]
        if row['class_name'] != expected['name'] or any(
            row[key] != expected[key] for key in ('crop', 'task', 'disease')
        ):
            raise ValueError(f'class mapping/code mismatch at manifest row {line}')
        split = row['split']
        if split not in SPLITS:
            raise ValueError(f'invalid split at manifest row {line}')
        rel = PurePosixPath(row['relative_path'].replace('\\', '/'))
        if rel.is_absolute() or '..' in rel.parts or not row['relative_path']:
            raise ValueError(f'unsafe image path at manifest row {line}')
        key = rel.as_posix().casefold()
        if key in seen_paths:
            raise ValueError(f'duplicate image path at manifest row {line}')
        seen_paths.add(key)
        image_path = (data_root / Path(*rel.parts)).resolve()
        if data_root not in image_path.parents or not image_path.is_file():
            raise ValueError(f'missing or escaped image path at manifest row {line}')
        expected_hash = row['source_sha256'].lower()
        derived_hash = row['derived_sha256'].lower()
        if len(expected_hash) != 64 or len(derived_hash) != 64:
            raise ValueError(f'invalid image hash at manifest row {line}')
        if _sha256(image_path) != derived_hash:
            raise ValueError(f'derived_sha256 mismatch at manifest row {line}')
        hash_splits[expected_hash].add(split)
        group = row['group_id'].strip()
        if not group:
            raise ValueError(f'missing group_id at manifest row {line}')
        group_splits[group].add(split)
    if any(len(splits) > 1 for splits in hash_splits.values()):
        raise ValueError('identical source image hashes cross split boundaries')
    if any(len(splits) > 1 for splits in group_splits.values()):
        raise ValueError('group_id crosses split boundaries')
    counts = {
        split: Counter(int(row['class_id']) for row in rows if row['split'] == split)
        for split in SPLITS
    }
    for split, class_counts in counts.items():
        if set(class_counts) != set(class_map):
            raise ValueError(f'split {split} must contain all configured classes')
    return rows


class PepperClassificationDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], data_root: Path, image_size: int = 224):
        class AspectPreservingPad:
            def __init__(self, size: int):
                self.size = size

            def __call__(self, image: Image.Image) -> Image.Image:
                # Fill is approximately ImageNet mean so normalized padding is
                # near zero; the full plant image remains visible without warp.
                return ImageOps.pad(
                    image,
                    (self.size, self.size),
                    method=Image.Resampling.BILINEAR,
                    color=(124, 116, 104),
                )

        self.rows = rows
        self.data_root = data_root.resolve()
        self.transform = Compose(
            [
                AspectPreservingPad(image_size),
                ToTensor(),
                Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ]
        )

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        path = self.data_root / Path(*PurePosixPath(row['relative_path']).parts)
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert('RGB')
            return self.transform(image), int(row['class_id'])
