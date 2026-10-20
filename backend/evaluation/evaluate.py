"""Image-level service evaluation, with no Django or AI import until inference.

No training, downloading, DB access, image annotation or input-file writes.
Bounding-box evaluation is deliberately gated; see DATASET_DESIGN.md.
"""

import argparse
import contextlib
import csv
import hashlib
import importlib.metadata
import io
import json
import math
import os
import platform
import random
import re
import sys
import tempfile
import time
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

LABELS = {
    'PEPPER_ANTHRACNOSE': 'pepper',
    'PEPPER_POWDERY_MILDEW': 'pepper',
    'CUCUMBER_DOWNY_MILDEW': 'cucumber',
    'CUCUMBER_POWDERY_MILDEW': 'cucumber',
    'TOMATO_POWDERY_MILDEW': 'tomato',
}
FIELDS = (
    'image_id,relative_path,sha256,split,group_id,origin_id,category,subcategory,crop,'
    'target_labels,review_status,label_evidence,source_id,source_version,license_id,'
    'license_review,training_overlap'
).split(',')
CATEGORIES = {
    'supported': {'disease'},
    'normal': {'healthy'},
    'unsupported': {'crop', 'disease', 'general_plant'},
    'quality': {'blur', 'dark', 'bright', 'small_lesion'},
}
CONFIG_KEYS = {
    'schema_version',
    'mode',
    'split',
    'confidence_threshold',
    'prediction_confidence_floor',
    'nms_iou',
    'max_det',
    'imgsz',
    'tta',
    'device',
    'seed',
    'deterministic',
    'class_semantics',
    'class_contract',
}
TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')


class EvaluationError(ValueError):
    """An actionable error that contains no private file paths."""


def require(condition, message):
    if not condition:
        raise EvaluationError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def number(value, lower, upper, field):
    require(
        type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper,
        f'Invalid numeric range: {field}.',
    )


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key.')
        result[key] = value
    return result


def load_config(path):
    try:
        config = json.loads(
            Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationError('Cannot read configuration JSON.') from exc
    require(
        isinstance(config, dict) and set(config) == CONFIG_KEYS,
        'Configuration keys do not match schema v1.',
    )
    require(
        type(config['schema_version']) is int and config['schema_version'] == 1,
        'Unsupported schema version.',
    )
    require(
        config['mode'] == 'image',
        'Only image mode is implemented; bbox requires restored class semantics.',
    )
    require(config['split'] in ('validation', 'test'), 'Invalid evaluation split.')
    for key in ('confidence_threshold', 'prediction_confidence_floor', 'nms_iou'):
        number(config[key], 0, 1, key)
    require(
        config['prediction_confidence_floor'] <= config['confidence_threshold'],
        'Prediction floor must not exceed the acceptance threshold.',
    )
    for key, low, high in (('imgsz', 32, 4096), ('max_det', 1, 3000), ('seed', 0, 2**32 - 1)):
        require(type(config[key]) is int and low <= config[key] <= high, f'Invalid integer: {key}.')
    require(config['imgsz'] % 32 == 0, 'imgsz must be a multiple of 32.')
    require(
        type(config['tta']) is bool and type(config['deterministic']) is bool,
        'tta and deterministic must be booleans.',
    )
    require(
        isinstance(config['device'], str)
        and re.fullmatch(r'cpu|[0-9]+', config['device']) is not None,
        'Use cpu or a single CUDA device index.',
    )
    require(
        config['class_semantics'] in ('unresolved', 'verified'), 'Invalid class semantics status.'
    )
    contract = config['class_contract']
    require(isinstance(contract, list) and len(contract) > 0, 'Empty class contract.')
    for index, item in enumerate(contract):
        require(
            isinstance(item, dict) and set(item) == {'id', 'name', 'service_label'},
            'Invalid class contract entry.',
        )
        require(
            type(item['id']) is int and item['id'] == index,
            'Class IDs must be unique, ordered, contiguous integers from zero.',
        )
        require(
            isinstance(item['name'], str)
            and bool(item['name'].strip())
            and len(item['name']) <= 100,
            'Invalid class name.',
        )
        require(
            isinstance(item['service_label'], str) and item['service_label'] in LABELS,
            'Unknown service label.',
        )
    require(
        {item['service_label'] for item in contract} == set(LABELS),
        'Comparison contract must cover all five service labels.',
    )
    return config


def inspect_image(path):
    # Pillow is a base service dependency; no Ultralytics/torch needed for preflight.
    from PIL import Image

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path) as image:
                require(image.format in ('JPEG', 'PNG', 'WEBP'), 'Unsupported image format.')
                image.verify()
            with Image.open(path) as image:
                image.load()
    except EvaluationError:
        raise
    except Exception as exc:
        raise EvaluationError('Invalid or unsafe image content.') from exc


def load_manifest(path, root, split, score=True):
    """Validate ALL splits, preventing hidden validation/test leakage."""
    root = Path(root).resolve()
    require(root.is_dir(), 'Data root does not exist.')
    try:
        with Path(path).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            require(reader.fieldnames == FIELDS, 'Manifest header must match the example exactly.')
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise EvaluationError('Cannot read manifest CSV.') from exc
    require(bool(rows), 'Manifest is empty; no evaluation can be performed.')
    ids, hashes, groups, origins = set(), set(), {}, {}
    selected = []
    for index, row in enumerate(rows, start=2):
        prefix = f'Manifest row {index}: '
        require(
            set(row) == set(FIELDS) and all(isinstance(v, str) for v in row.values()),
            prefix + 'invalid CSV row width.',
        )
        for key in (
            'image_id',
            'group_id',
            'origin_id',
            'source_id',
            'source_version',
            'license_id',
            'crop',
        ):
            require(TOKEN.fullmatch(row[key]) is not None, prefix + f'invalid {key} token.')
        require(
            not row['label_evidence'] or TOKEN.fullmatch(row['label_evidence']) is not None,
            prefix + 'label_evidence must be an anonymous reference ID.',
        )
        require(row['image_id'] not in ids, prefix + 'duplicate image_id.')
        ids.add(row['image_id'])
        require(row['split'] in ('validation', 'test'), prefix + 'invalid split.')
        for field, seen in (('group_id', groups), ('origin_id', origins)):
            require(
                seen.setdefault(row[field], row['split']) == row['split'],
                prefix + f'{field} crosses splits.',
            )
        require(row['category'] in CATEGORIES, prefix + 'invalid category.')
        require(row['subcategory'] in CATEGORIES[row['category']], prefix + 'invalid subcategory.')
        require(
            row['review_status'] in ('verified', 'unreviewed'), prefix + 'invalid review status.'
        )
        require(
            row['license_review'] in ('approved', 'pending'), prefix + 'invalid license review.'
        )
        require(
            row['training_overlap'] in ('unknown', 'not_found', 'overlap'),
            prefix + 'invalid training overlap status.',
        )
        targets = row['target_labels'].split('|') if row['target_labels'] else []
        require(
            len(targets) == len(set(targets))
            and all(t in LABELS or t in ('healthy', 'unsupported') for t in targets),
            prefix + 'invalid target labels.',
        )
        if targets:
            require(
                not (set(targets) & {'healthy', 'unsupported'}) or len(targets) == 1,
                prefix + 'negative and disease labels cannot be mixed.',
            )
            if row['category'] == 'supported':
                require(
                    all(t in LABELS for t in targets), prefix + 'supported needs disease labels.'
                )
            if row['category'] in ('normal', 'unsupported'):
                expected = 'healthy' if row['category'] == 'normal' else 'unsupported'
                require(targets == [expected], prefix + 'category and target disagree.')
            require(
                all(t not in LABELS or LABELS[t] == row['crop'] for t in targets),
                prefix + 'crop and disease disagree.',
            )
        if row['category'] == 'normal':
            require(row['crop'] in set(LABELS.values()), prefix + 'normal crop is not supported.')
        relative = PurePosixPath(row['relative_path'])
        require(
            bool(row['relative_path'])
            and not relative.is_absolute()
            and '..' not in relative.parts
            and '\\' not in row['relative_path']
            and ':' not in row['relative_path'],
            prefix + 'use a safe relative POSIX path.',
        )
        image_path = (root / relative).resolve()
        require(
            image_path.is_relative_to(root) and image_path.is_file(),
            prefix + 'image missing or outside data root.',
        )
        require(HASH.fullmatch(row['sha256']) is not None, prefix + 'invalid SHA-256.')
        require(sha256(image_path) == row['sha256'], prefix + 'image SHA-256 mismatch.')
        require(row['sha256'] not in hashes, prefix + 'duplicate image content.')
        hashes.add(row['sha256'])
        inspect_image(image_path)
        if row['split'] == split:
            require(row['license_review'] == 'approved', prefix + 'usage review pending.')
            require(row['training_overlap'] != 'overlap', prefix + 'known training overlap.')
            if score and row['category'] != 'quality':
                require(
                    row['review_status'] == 'verified'
                    and bool(targets)
                    and bool(row['label_evidence']),
                    prefix + 'verified ground truth required.',
                )
            selected.append({**row, 'targets': targets, '_path': image_path})
    require(bool(selected), 'Selected split is empty.')
    return selected


def validate_names(names, config):
    expected = {c['id']: c['name'] for c in config['class_contract']}
    require(
        isinstance(names, dict) and all(type(k) is int for k in names) and names == expected,
        'Model names do not match the configured contract.',
    )


def select_prediction(boxes, config):
    """Validate every returned box, then select first maximum at the inclusive threshold."""
    validated = []
    contract = config['class_contract']
    for box in boxes:
        require(
            isinstance(box, dict) and set(box) == {'class_id', 'confidence'},
            'Malformed prediction box.',
        )
        class_id, confidence = box['class_id'], box['confidence']
        number(class_id, 0, len(contract) - 1, 'class_id')
        require(float(class_id).is_integer(), 'Class ID must be integral.')
        number(confidence, 0, 1, 'confidence')
        class_id = int(class_id)
        validated.append(
            {
                'class_id': class_id,
                'confidence': float(confidence),
                'service_label': contract[class_id]['service_label'],
            }
        )
    eligible = [b for b in validated if b['confidence'] >= config['confidence_threshold']]
    selected = max(eligible, key=lambda b: b['confidence']) if eligible else None
    return validated, selected


def ratio(numerator, denominator):
    return {
        'numerator': numerator,
        'denominator': denominator,
        'value': numerator / denominator if denominator else None,
    }


def metrics(records):
    """Single-label service metrics only; neither object detection AP nor raw-class accuracy."""
    require(records, 'Metrics require a non-empty evaluation split.')
    require(
        all(
            r['review_status'] == 'verified' and r['target_labels'] and r['label_evidence']
            for r in records
            if r['category'] != 'quality'
        ),
        'Metrics require reviewed ground truth on every non-quality image.',
    )
    primary = [r for r in records if r['category'] != 'quality' and len(r['target_labels']) == 1]
    supported = [r for r in primary if r['category'] == 'supported']
    accepted = [r for r in primary if r['decision'] == 'accepted']

    def correct(row):
        return row['predicted_label'] in row['target_labels']

    per_class = {}
    for label in LABELS:
        tp = sum(r['predicted_label'] == label and correct(r) for r in primary)
        fp = sum(r['predicted_label'] == label and not correct(r) for r in primary)
        fn = sum(r['target_labels'] == [label] and r['predicted_label'] != label for r in primary)
        per_class[label] = {
            'tp': tp,
            'fp': fp,
            'fn': fn,
            'precision': ratio(tp, tp + fp),
            'recall': ratio(tp, tp + fn),
        }
    confusion = {}
    for row in primary:
        truth = row['target_labels'][0]
        predicted = row['predicted_label'] or 'abstain'
        confusion.setdefault(truth, {})[predicted] = confusion.get(truth, {}).get(predicted, 0) + 1
    negative_rates = {}
    for category in ('normal', 'unsupported'):
        subset = [r for r in primary if r['category'] == category]
        negative_rates[category] = ratio(
            sum(r['decision'] == 'accepted' for r in subset), len(subset)
        )
    strata = {}
    for category in CATEGORIES:
        subset = [r for r in records if r['category'] == category]
        strata[category] = {
            'count': len(subset),
            'abstention_rate': ratio(sum(r['decision'] == 'abstain' for r in subset), len(subset)),
        }
    multi = [r for r in records if len(r['target_labels']) > 1 and r['category'] != 'quality']
    return {
        'scope': 'service_mapping_single_label_image_level',
        'primary_count': len(primary),
        'supported_match_rate': ratio(sum(correct(r) for r in supported), len(supported)),
        'abstention_rate': ratio(sum(r['decision'] == 'abstain' for r in primary), len(primary)),
        'accepted_error_rate': ratio(sum(not correct(r) for r in accepted), len(accepted)),
        'negative_false_positive_rates': negative_rates,
        'per_service_label': per_class,
        'confusion_matrix': {'rows': 'ground_truth', 'columns': 'prediction', 'counts': confusion},
        'category_diagnostics': strata,
        'multilabel_diagnostic': {
            'count': len(multi),
            'top1_in_truth_rate': ratio(sum(correct(r) for r in multi), len(multi)),
            'included_in_primary': False,
        },
        'quality_included_in_primary': False,
        'raw_class_metrics': None,
        'mAP': None,
    }


def environment():
    versions = {}
    for package in ('torch', 'torchvision', 'ultralytics', 'opencv-python', 'numpy', 'Pillow'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {
        'python': platform.python_version(),
        'os': platform.system(),
        'machine': platform.machine(),
        'packages': versions,
    }


class YoloPredictor:
    def __init__(self, model_path, config):
        import numpy as np
        import torch
        from ultralytics import YOLO

        random.seed(config['seed'])
        np.random.seed(config['seed'])
        torch.manual_seed(config['seed'])
        torch.use_deterministic_algorithms(config['deterministic'])
        torch.backends.cudnn.deterministic = config['deterministic']
        torch.backends.cudnn.benchmark = False
        require(
            config['device'] == 'cpu' or torch.cuda.is_available(),
            'CUDA requested but unavailable.',
        )
        self.model = YOLO(str(model_path), task='detect')
        require(self.model.task == 'detect', 'Model must be a detection model.')
        self.names = self.model.names
        self.runtime = {
            'cuda_available': torch.cuda.is_available(),
            'cuda_build': torch.version.cuda,
            'device_requested': config['device'],
            'torch_threads': torch.get_num_threads(),
        }

    def predict(self, path, config):
        results = self.model.predict(
            source=str(path),
            imgsz=config['imgsz'],
            augment=config['tta'],
            conf=config['prediction_confidence_floor'],
            iou=config['nms_iou'],
            max_det=config['max_det'],
            device=config['device'],
            batch=1,
            half=False,
            rect=True,
            agnostic_nms=False,
            classes=None,
            save=False,
            save_txt=False,
            save_crop=False,
            save_conf=False,
            show=False,
            verbose=False,
        )
        require(len(results) == 1 and results[0].boxes is not None, 'Invalid detection result.')
        return [
            {'class_id': float(b.cls.item()), 'confidence': float(b.conf.item())}
            for b in results[0].boxes
        ]


def run(
    config,
    model_path,
    manifest_path,
    data_root,
    output,
    *,
    score=True,
    validate_only=False,
    predictor_factory=YoloPredictor,
):
    model_path = Path(model_path).resolve()
    require(
        model_path.is_file() and model_path.suffix.lower() == '.pt',
        'An existing local .pt model is required; downloads are disabled.',
    )
    model_hash = sha256(model_path)
    manifest_hash = sha256(manifest_path)
    rows = load_manifest(manifest_path, data_root, config['split'], score=score)
    summary = {
        'schema_version': 1,
        'model_sha256': model_hash,
        'manifest_sha256': manifest_hash,
        'selected_count': len(rows),
        'config': config,
        'training_overlap_counts': dict(Counter(r['training_overlap'] for r in rows)),
        'independence': 'not_proven_by_this_tool',
        'limitations': [
            'Exact hashes and declared groups do not prove training independence.',
            'Service-label mapping does not establish raw-class semantics.',
            'No bounding-box metrics are computed.',
        ],
    }
    if validate_only:
        return {**summary, 'status': 'input_validation_only', 'metrics': None}
    require(output is not None, 'A new output directory is required.')
    output = Path(output).resolve()
    require(not output.exists(), 'Output already exists; choose a new directory.')
    require(
        not output.is_relative_to(Path(data_root).resolve()),
        'Output must be outside the data root.',
    )
    records = []
    # AI libraries can log absolute paths. Keep third-party output out of reports/terminal.
    with tempfile.TemporaryDirectory(prefix='farm-evaluation-') as runtime_dir:
        previous = {
            k: os.environ.get(k)
            for k in ('YOLO_CONFIG_DIR', 'YOLO_OFFLINE', 'CUBLAS_WORKSPACE_CONFIG')
        }
        os.environ.update(
            YOLO_CONFIG_DIR=runtime_dir, YOLO_OFFLINE='true', CUBLAS_WORKSPACE_CONFIG=':4096:8'
        )
        try:
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                start = time.perf_counter()
                predictor = predictor_factory(model_path, config)
                load_seconds = time.perf_counter() - start
                validate_names(predictor.names, config)
                for row in rows:
                    require(sha256(row['_path']) == row['sha256'], 'Image changed after preflight.')
                    start = time.perf_counter()
                    boxes, selected = select_prediction(
                        predictor.predict(row['_path'], config), config
                    )
                    seconds = time.perf_counter() - start
                    records.append(
                        {
                            **{
                                key: row[key]
                                for key in FIELDS
                                if key not in ('relative_path', 'target_labels')
                            },
                            'target_labels': row['targets'],
                            'boxes': boxes,
                            'predicted_class_id': selected['class_id'] if selected else None,
                            'predicted_label': selected['service_label'] if selected else None,
                            'confidence': selected['confidence'] if selected else None,
                            'decision': 'accepted' if selected else 'abstain',
                            'elapsed_seconds': seconds,
                        }
                    )
        except EvaluationError:
            raise
        except Exception as exc:
            raise EvaluationError(
                'Model loading or inference failed; no report was written.'
            ) from exc
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    require(sha256(model_path) == model_hash, 'Model changed during execution.')
    require(sha256(manifest_path) == manifest_hash, 'Manifest changed during execution.')
    report = {
        **summary,
        'status': 'scored' if score else 'predictions_only',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'environment': environment(),
        'runtime': predictor.runtime,
        'model_load_seconds': load_seconds,
        'tool_sha256': sha256(__file__),
        'metrics': metrics(records) if score else None,
        'timing_scope': 'serial predict calls; first includes warmup; excludes API/DB',
        'records': records,
    }
    # Pre-serialize before creating output; inputs and previous reports are never overwritten.
    serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.evaluation-stage-', dir=output.parent) as stage:
        stage = Path(stage)
        (stage / 'report.json').write_text(serialized + '\n', encoding='utf-8')
        with (stage / 'predictions.csv').open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
                        for k, v in record.items()
                    }
                )
        # Readers see both completed output files or neither.
        stage.rename(output)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--check-config', action='store_true')
    parser.add_argument('--model')
    parser.add_argument('--manifest')
    parser.add_argument('--data-root')
    parser.add_argument('--output')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--predict-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.check_config:
            print('Configuration valid. No model or data loaded; no metrics computed.')
            return 0
        require(
            all((args.model, args.manifest, args.data_root)),
            '--model, --manifest and --data-root are required.',
        )
        report = run(
            config,
            args.model,
            args.manifest,
            args.data_root,
            args.output,
            score=not args.predict_only,
            validate_only=args.validate_only,
        )
        print(
            json.dumps(
                {
                    'status': report['status'],
                    'selected_count': report['selected_count'],
                    'model_sha256': report['model_sha256'],
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (EvaluationError, OSError) as exc:
        message = str(exc) if isinstance(exc, EvaluationError) else 'Local file operation failed.'
        print(f'Evaluation blocked: {message}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
