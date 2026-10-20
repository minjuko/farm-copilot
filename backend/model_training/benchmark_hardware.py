"""Measure MobileNetV3-Small training-step and image-input throughput.

This is a hardware benchmark only. It does not use labels, create splits, save
checkpoints, download pretrained weights, or report model quality.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import time
from pathlib import Path
from typing import Any

import torch
from PIL import Image, ImageOps
from torch import nn


def _synchronize(device: torch.device) -> None:
    if device.type == 'cuda':
        torch.cuda.synchronize(device)


def _create_model() -> nn.Module:
    from torchvision.models import mobilenet_v3_small

    # Random initialization keeps this measurement offline and avoids fetching
    # ImageNet weights. It does not change the model's forward/backward workload.
    return mobilenet_v3_small(weights=None, num_classes=3)


def _measure_training_step(
    device: torch.device, batch_size: int, image_size: int, warmup: int, iterations: int
) -> dict[str, Any]:
    model = _create_model().to(device).train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    inputs = torch.rand(batch_size, 3, image_size, image_size, device=device)
    labels = torch.randint(0, 3, (batch_size,), device=device)
    elapsed_steps: list[float] = []

    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats(device)

    for step in range(warmup + iterations):
        optimizer.zero_grad(set_to_none=True)
        _synchronize(device)
        started = time.perf_counter()
        loss = criterion(model(inputs), labels)
        loss.backward()
        optimizer.step()
        _synchronize(device)
        elapsed = time.perf_counter() - started
        if step >= warmup:
            elapsed_steps.append(elapsed)

    mean_seconds = statistics.mean(elapsed_steps)
    return {
        'batch_size': batch_size,
        'warmup_steps_excluded': warmup,
        'measured_steps': iterations,
        'mean_step_seconds': mean_seconds,
        'median_step_seconds': statistics.median(elapsed_steps),
        'images_per_second': batch_size / mean_seconds,
        'estimated_seconds_per_epoch_for_40_images': math.ceil(40 / batch_size)
        * mean_seconds,
        'estimated_seconds_per_epoch_for_900_images': math.ceil(900 / batch_size)
        * mean_seconds,
        'peak_cuda_memory_bytes': torch.cuda.max_memory_allocated(device)
        if device.type == 'cuda'
        else None,
    }


def _measure_image_decode(images_dir: Path, image_size: int) -> dict[str, Any]:
    paths = sorted(
        path
        for path in images_dir.rglob('*')
        if path.is_file() and path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
    )
    started = time.perf_counter()
    decoded = 0
    errors: list[str] = []
    for path in paths:
        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.resize((image_size, image_size), Image.Resampling.BILINEAR).load()
            decoded += 1
        except (OSError, ValueError) as exc:
            errors.append(f'{path.name}: {exc}')
    elapsed = time.perf_counter() - started
    return {
        'images_found': len(paths),
        'images_decoded': decoded,
        'decode_errors': errors,
        'elapsed_seconds': elapsed,
        'images_per_second': decoded / elapsed if elapsed else None,
        'scope': 'PIL open + EXIF transpose + RGB conversion + resize; excludes model and storage upload',
    }


def run_benchmark(
    *,
    device_name: str = 'auto',
    batches: tuple[int, ...] = (4, 8, 16),
    image_size: int = 224,
    warmup: int = 1,
    iterations: int = 3,
    images_dir: Path | None = None,
) -> dict[str, Any]:
    if image_size < 32 or warmup < 0 or iterations < 1 or not batches:
        raise ValueError('invalid benchmark settings')
    if any(batch < 2 for batch in batches):
        raise ValueError('training-step benchmark batch sizes must be at least 2 (BatchNorm)')
    if device_name == 'cuda' and not torch.cuda.is_available():
        raise ValueError('CUDA was requested but is unavailable')
    use_cuda = device_name == 'cuda' or (device_name == 'auto' and torch.cuda.is_available())
    device = torch.device('cuda' if use_cuda else 'cpu')
    result: dict[str, Any] = {
        'benchmark': 'mobilenet_v3_small_training_step',
        'device': str(device),
        'python': platform.python_version(),
        'torch': torch.__version__,
        'torchvision': __import__('torchvision').__version__,
        'cuda_build': torch.version.cuda,
        'cuda_available': torch.cuda.is_available(),
        'cpu_threads': torch.get_num_threads(),
        'gpu_name': torch.cuda.get_device_name(device) if device.type == 'cuda' else None,
        'image_size': image_size,
        'pretrained_weights': False,
        'weights_note': 'Random initialization; no network download. Compute-path benchmark only.',
        'measurements': [
            _measure_training_step(device, batch, image_size, warmup, iterations)
            for batch in batches
        ],
    }
    if images_dir is not None:
        if not images_dir.is_dir():
            raise ValueError(f'images directory does not exist: {images_dir}')
        result['image_decode'] = _measure_image_decode(images_dir, image_size)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='auto')
    parser.add_argument('--batches', type=int, nargs='+', default=(4, 8, 16))
    parser.add_argument('--image-size', type=int, default=224)
    parser.add_argument('--warmup', type=int, default=1)
    parser.add_argument('--iterations', type=int, default=3)
    parser.add_argument('--images-dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_benchmark(
            device_name=args.device,
            batches=tuple(args.batches),
            image_size=args.image_size,
            warmup=args.warmup,
            iterations=args.iterations,
            images_dir=args.images_dir,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            parser.error(f'output already exists: {args.output}')
        args.output.write_text(serialized + '\n', encoding='utf-8')
    print(serialized)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
