"""Create local, lower-resolution variants of an existing image subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.webp'}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _target_size(width: int, height: int, longest: int) -> tuple[int, int]:
    scale = min(1.0, longest / max(width, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def create_variants(
    source_dir: Path,
    output_dir: Path,
    sizes: tuple[int, ...] = (512, 768, 1024),
    quality: int = 90,
) -> dict[str, Any]:
    if not source_dir.is_dir():
        raise ValueError(f'source directory does not exist: {source_dir}')
    if output_dir.exists():
        raise ValueError(f'output directory already exists: {output_dir}')
    if not sizes or any(size < 32 for size in sizes):
        raise ValueError('target sizes must be at least 32 pixels')
    if not 1 <= quality <= 100:
        raise ValueError('quality must be between 1 and 100')
    images = sorted(
        p for p in source_dir.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        raise ValueError('no supported images found')

    started = time.perf_counter()
    output_dir.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    try:
        for path in images:
            with Image.open(path) as source:
                oriented = ImageOps.exif_transpose(source).convert('RGB')
                original_size = oriented.size
                source_hash = _sha256(path)
                for longest in sizes:
                    width, height = _target_size(*original_size, longest)
                    resized = oriented.copy()
                    if resized.size != (width, height):
                        resized = resized.resize((width, height), Image.Resampling.LANCZOS)
                    variant_dir = output_dir / f'max_{longest}'
                    variant_dir.mkdir(exist_ok=True)
                    target = variant_dir / f'{path.stem}.jpg'
                    if target.exists():
                        raise ValueError(f'output collision: {target}')
                    resized.save(target, format='JPEG', quality=quality, optimize=True)
                    with Image.open(target) as check:
                        check.load()
                        if check.mode != 'RGB' or check.size != (width, height):
                            raise ValueError(f'variant validation failed: {target}')
                        if check.getexif().get(274) is not None:
                            raise ValueError(f'EXIF orientation tag remains: {target}')
                    records.append(
                        {
                            'source_name': path.name,
                            'source_sha256': source_hash,
                            'source_width': original_size[0],
                            'source_height': original_size[1],
                            'max_dimension': longest,
                            'output_name': target.relative_to(output_dir).as_posix(),
                            'output_sha256': _sha256(target),
                            'output_width': width,
                            'output_height': height,
                            'output_bytes': target.stat().st_size,
                            'aspect_ratio_error': abs(
                                width / height - original_size[0] / original_size[1]
                            ),
                        }
                    )
        baseline_bytes = sum(path.stat().st_size for path in images)
        for longest in sizes:
            rows = [row for row in records if row['max_dimension'] == longest]
            total_bytes = sum(row['output_bytes'] for row in rows)
            summaries[str(longest)] = {
                'image_count': len(rows),
                'total_bytes': total_bytes,
                'mean_bytes': statistics.mean(row['output_bytes'] for row in rows),
                'reduction_vs_source_percent': 100 * (1 - total_bytes / baseline_bytes),
                'decoded_rgb_images': len(rows),
                'orientation_tag_removed': True,
                'max_aspect_ratio_error': max(row['aspect_ratio_error'] for row in rows),
            }
        result = {
            'source_dir': str(source_dir),
            'source_image_count': len(images),
            'source_bytes': baseline_bytes,
            'quality': quality,
            'resampling': 'LANCZOS',
            'elapsed_seconds': time.perf_counter() - started,
            'variants': summaries,
            'files': records,
            'limitation': 'No classifier accuracy or fine-lesion retention was evaluated.',
        }
        (output_dir / 'resize_report.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )
        return result
    except Exception:
        # Keep partial output for inspection; never delete or alter the source.
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--sizes', nargs='+', type=int, default=(512, 768, 1024))
    parser.add_argument('--quality', type=int, default=90)
    args = parser.parse_args()
    try:
        result = create_variants(args.source_dir, args.output_dir, tuple(args.sizes), args.quality)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
