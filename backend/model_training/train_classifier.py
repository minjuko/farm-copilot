"""Train/evaluate a compact 3-class pepper classifier from a strict CSV manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import torch
from torch import nn
from torch.utils.data import DataLoader

from model_training.dataset import (
    CLASS_MAP,
    PepperClassificationDataset,
    load_class_map,
    load_manifest,
)
from model_training.metrics import classification_metrics


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def create_model(pretrained: bool = True, class_count: int | None = None) -> nn.Module:
    from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

    weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    model = mobilenet_v3_small(weights=weights)
    model.classifier[-1] = nn.Linear(
        model.classifier[-1].in_features, class_count or len(CLASS_MAP)
    )
    return model


def _evaluate(
    model: nn.Module, loader: DataLoader, device: torch.device,
    class_map: dict[int, dict[str, str]] | None = None,
) -> tuple[dict, list[float], float, list[int], list[int], list[float]]:
    class_map = class_map or CLASS_MAP
    model.eval()
    truth: list[int] = []
    predicted: list[int] = []
    latency_ms: list[float] = []
    losses: list[float] = []
    confidences: list[float] = []
    criterion = nn.CrossEntropyLoss()
    with torch.inference_mode():
        for images, labels in loader:
            images = images.to(device)
            if device.type == 'cuda':
                torch.cuda.synchronize(device)
            started = time.perf_counter()
            logits = model(images)
            if device.type == 'cuda':
                torch.cuda.synchronize(device)
            elapsed = (time.perf_counter() - started) * 1000 / len(images)
            latency_ms.extend([elapsed] * len(images))
            losses.append(float(criterion(logits, labels.to(device)).cpu()))
            truth.extend(int(value) for value in labels.tolist())
            probabilities = logits.softmax(dim=1)
            confidence, guesses = probabilities.max(dim=1)
            predicted.extend(int(value) for value in guesses.cpu().tolist())
            confidences.extend(float(value) for value in confidence.cpu().tolist())
    return (
        classification_metrics(truth, predicted, list(class_map)),
        latency_ms,
        statistics.mean(losses),
        truth,
        predicted,
        confidences,
    )


def train(
    manifest_path: Path,
    data_root: Path,
    output_dir: Path,
    *,
    epochs: int = 5,
    batch_size: int = 16,
    image_size: int = 224,
    learning_rate: float = 0.001,
    seed: int = 2026,
    pretrained: bool = True,
    device_name: str = 'auto',
    model_factory: Callable[[], nn.Module] | None = None,
    architecture_name: str = 'mobilenet_v3_small',
    class_map: dict[int, dict[str, str]] | None = None,
) -> dict[str, Any]:
    if epochs < 1 or batch_size < 1 or image_size < 32 or learning_rate <= 0:
        raise ValueError('invalid training hyperparameters')
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f'output directory already exists: {output_dir}')
    class_map = class_map or CLASS_MAP
    rows = load_manifest(manifest_path, data_root, class_map)
    device = torch.device(
        'cuda'
        if device_name == 'auto' and torch.cuda.is_available()
        else 'cpu'
        if device_name == 'auto'
        else device_name
    )
    if device.type == 'cuda' and not torch.cuda.is_available():
        raise ValueError('CUDA was requested but is unavailable')
    set_seed(seed)
    datasets = {
        split: PepperClassificationDataset(
            [row for row in rows if row['split'] == split], data_root, image_size
        )
        for split in ('train', 'val', 'test')
    }
    generator = torch.Generator().manual_seed(seed)
    loaders = {
        split: DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=(split == 'train'),
            num_workers=0,
            generator=generator if split == 'train' else None,
        )
        for split, dataset in datasets.items()
    }
    model = (model_factory() if model_factory else create_model(
        pretrained=pretrained, class_count=len(class_map)
    )).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()
    history: list[dict[str, float | int]] = []
    best_macro_f1 = -1.0
    best_state: dict[str, torch.Tensor] | None = None
    output_dir.mkdir(parents=True)
    checkpoint_path = output_dir / 'best_model.pt'
    for epoch in range(1, epochs + 1):
        model.train()
        losses: list[float] = []
        for images, labels in loaders['train']:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        val_metrics, _, val_loss, _, _, _ = _evaluate(model, loaders['val'], device, class_map)
        row = {
            'epoch': epoch,
            'train_loss': statistics.mean(losses),
            'val_loss': val_loss,
            'val_macro_f1': val_metrics['macro_f1'],
        }
        history.append(row)
        if val_metrics['macro_f1'] > best_macro_f1:
            best_macro_f1 = val_metrics['macro_f1']
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            temporary = checkpoint_path.with_suffix('.tmp')
            torch.save(
                {
                    'state_dict': model.state_dict(),
                    'class_map': class_map,
                    'image_size': image_size,
                    'architecture': architecture_name,
                    'epoch': epoch,
                    'val_macro_f1': best_macro_f1,
                },
                temporary,
            )
            os.replace(temporary, checkpoint_path)

    if best_state is None:
        raise RuntimeError('training did not produce a validation checkpoint')
    model.load_state_dict(best_state)
    model.to(device)
    test_metrics, latency, _, test_truth, test_predictions, test_confidences = _evaluate(
        model, loaders['test'], device, class_map
    )
    prediction_fields = [
        'relative_path',
        'true_class_id',
        'true_class_name',
        'predicted_class_id',
        'predicted_class_name',
        'confidence',
        'correct',
    ]
    prediction_rows = []
    for row, actual, predicted, confidence in zip(
        datasets['test'].rows, test_truth, test_predictions, test_confidences
    ):
        prediction_rows.append(
            {
                'relative_path': row['relative_path'],
                'true_class_id': actual,
                'true_class_name': class_map[actual]['name'],
                'predicted_class_id': predicted,
                'predicted_class_name': class_map[predicted]['name'],
                'confidence': confidence,
                'correct': actual == predicted,
            }
        )
    for filename, result_rows in (
        ('test_predictions.csv', prediction_rows),
        ('test_errors.csv', [row for row in prediction_rows if not row['correct']]),
    ):
        with (output_dir / filename).open('x', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=prediction_fields)
            writer.writeheader()
            writer.writerows(result_rows)
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    versions = {'python': platform.python_version(), 'torch': torch.__version__}
    try:
        import torchvision

        versions['torchvision'] = torchvision.__version__
    except Exception:
        versions['torchvision'] = 'unavailable'
    run = {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'architecture': architecture_name,
        'pretrained': pretrained,
        'device': str(device),
        'epochs': epochs,
        'batch_size': batch_size,
        'image_size': image_size,
        'learning_rate': learning_rate,
        'seed': seed,
        'class_map': class_map,
        'manifest_sha256': manifest_hash,
        'split_counts': {
            split: dict(Counter(int(r['class_id']) for r in rows if r['split'] == split))
            for split in ('train', 'val', 'test')
        },
        'environment': versions,
        'test_metrics': test_metrics,
        'test_latency_ms_per_image': {
            'mean': statistics.mean(latency),
            'median': statistics.median(latency),
            'p95': sorted(latency)[max(0, int(0.95 * len(latency)) - 1)],
        },
        'checkpoint': checkpoint_path.name,
        'test_predictions': 'test_predictions.csv',
        'test_errors': 'test_errors.csv',
        'checkpoint_selection': 'best validation macro F1; test evaluated once after training',
    }
    with (output_dir / 'history.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(
            stream, fieldnames=['epoch', 'train_loss', 'val_loss', 'val_macro_f1']
        )
        writer.writeheader()
        writer.writerows(history)
    (output_dir / 'run.json').write_text(json.dumps(run, indent=2), encoding='utf-8')
    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--image-size', type=int, default=224)
    parser.add_argument('--learning-rate', type=float, default=0.001)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='auto')
    parser.add_argument('--no-pretrained', action='store_true')
    parser.add_argument('--class-config', type=Path, help='JSON class contract; defaults to legacy 3-class')
    args = parser.parse_args(argv)
    try:
        result = train(
            args.manifest,
            args.data_root,
            args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            image_size=args.image_size,
            learning_rate=args.learning_rate,
            seed=args.seed,
            pretrained=not args.no_pretrained,
            device_name=args.device,
            class_map=load_class_map(args.class_config),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
