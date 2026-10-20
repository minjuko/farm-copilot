"""Create a small, EXIF-corrected classification subset from an audited ZIP sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import random
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, ImageOps

TARGET = {'crop': '5', 'task': '1', 'disease': 'a7'}
CLASS = {'id': 1, 'name': 'pepper_anthracnose'}
SOURCE_FILE_KEY = '51651'
FIELDS = [
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
    'source_image_ref',
    'source_sha256',
    'derived_sha256',
    'capture_date',
    'capture_time',
    'risk',
    'grow',
    'area',
    'group_id',
    'group_evidence',
    'transform',
]


def _select(rows: list[dict[str, Any]], count: int, seed: int) -> list[dict[str, Any]]:
    if count < 1 or count > len(rows):
        raise ValueError(f'sample size must be between 1 and candidate count ({len(rows)})')
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get('risk') or 'unknown')].append(row)
    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    # Round-robin across risk strata, then deterministic random selection per stratum.
    risks = sorted(buckets)
    quotas = {risk: 0 for risk in risks}
    while sum(quotas.values()) < count:
        for risk in risks:
            if quotas[risk] < len(buckets[risk]) and sum(quotas.values()) < count:
                quotas[risk] += 1
    for risk in risks:
        group = sorted(buckets[risk], key=lambda row: row['image_ref'].casefold())
        selected.extend(rng.sample(group, quotas[risk]))
    return sorted(selected, key=lambda row: row['image_ref'].casefold())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare_subset(
    archive_path: Path,
    sample_report_path: Path,
    output_dir: Path,
    *,
    sample_size: int = 40,
    seed: int = 2026,
) -> dict[str, Any]:
    """Extract only chosen members from a prior audited sample into a new folder."""
    archive_path = archive_path.resolve()
    sample_report_path = sample_report_path.resolve()
    output_dir = output_dir.resolve()
    if not archive_path.is_file() or not sample_report_path.is_file():
        raise ValueError('archive and sample report must both exist')
    if output_dir.exists():
        raise ValueError(f'output directory already exists: {output_dir}')
    staging_dir = output_dir.with_name(f'{output_dir.name}.staging')
    if staging_dir.exists():
        raise ValueError(f'staging directory already exists: {staging_dir}')
    report = json.loads(sample_report_path.read_text(encoding='utf-8'))
    label_info = report.get('labels', {})
    if label_info.get('target_codes') != TARGET:
        raise ValueError('audited sample target class does not match the configured class')
    if label_info.get('paired_unique_refs', 0) != label_info.get('target_rows'):
        raise ValueError('audited sample contains unpaired or duplicate label references')
    if report.get('archive', {}).get('size_bytes') != archive_path.stat().st_size:
        raise ValueError('sample report archive size does not match the selected archive')
    candidates = report.get('sample', {}).get('files', [])
    if not candidates:
        raise ValueError('sample report has no audited image records')
    selected = _select(candidates, sample_size, seed)
    staging_dir.mkdir(parents=True)
    image_dir = staging_dir / 'images' / CLASS['name']
    image_dir.mkdir(parents=True)
    manifest_path = staging_dir / 'manifest.csv'
    seen_source_hashes: set[str] = set()
    rows: list[dict[str, str]] = []
    try:
        with zipfile.ZipFile(archive_path, metadata_encoding='cp949') as archive:
            by_ref = {row['image_ref']: row for row in selected}
            for info in archive.infolist():
                member_name = PurePosixPath(info.filename).name.casefold()
                matches = [
                    ref
                    for ref in by_ref
                    if PurePosixPath(ref.replace('\\', '/')).name.casefold() == member_name
                ]
                if not matches:
                    continue
                if len(matches) != 1:
                    raise ValueError(f'ambiguous archive basename: {member_name}')
                reference = matches[0]
                source_row = by_ref[reference]
                raw = archive.read(info)
                source_hash = _sha256(raw)
                if source_hash != source_row.get('sha256'):
                    raise ValueError(f'source hash differs from audited report: {reference}')
                if source_hash in seen_source_hashes:
                    raise ValueError('selected subset contains byte-identical source images')
                seen_source_hashes.add(source_hash)
                with Image.open(io.BytesIO(raw)) as image:
                    image = ImageOps.exif_transpose(image).convert('RGB')
                    image.load()
                    width, height = image.size
                    relative = Path('images') / CLASS['name'] / f'{source_hash[:16]}.jpg'
                    derived_path = staging_dir / relative
                    image.save(derived_path, format='JPEG', quality=95, optimize=True)
                derived_hash = hashlib.sha256(derived_path.read_bytes()).hexdigest()
                rows.append(
                    {
                        'relative_path': relative.as_posix(),
                        'split': 'unassigned',
                        'class_id': str(CLASS['id']),
                        'class_name': CLASS['name'],
                        **TARGET,
                        'dataset_key': '525',
                        'dataset_version': f'pepper-a7-tech-{sample_size}-v1',
                        'file_key': SOURCE_FILE_KEY,
                        'source_image_ref': reference,
                        'source_sha256': source_hash,
                        'derived_sha256': derived_hash,
                        'capture_date': str(source_row.get('date') or ''),
                        'capture_time': str(source_row.get('time') or ''),
                        'risk': str(source_row.get('risk') or ''),
                        'grow': str(source_row.get('grow') or ''),
                        'area': str(source_row.get('area') or ''),
                        'group_id': '',
                        'group_evidence': 'unknown; no plant identity verified',
                        'transform': f'exif_transpose; RGB; JPEG quality=95; {width}x{height}',
                    }
                )
                del by_ref[reference]
            if by_ref:
                raise ValueError(f'audited image(s) not found in archive: {len(by_ref)}')
        with manifest_path.open('x', newline='', encoding='utf-8-sig') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        result = {
            'dataset_version': f'pepper-a7-tech-{sample_size}-v1',
            'source_dataset_key': '525',
            'source_file_key': SOURCE_FILE_KEY,
            'source_archive_size_bytes': archive_path.stat().st_size,
            'source_sample_report_sha256': hashlib.sha256(
                sample_report_path.read_bytes()
            ).hexdigest(),
            'target_codes': TARGET,
            'class': CLASS,
            'images_written': len(rows),
            'seed': seed,
            'split': 'unassigned (single class; not a train/validation/test dataset)',
            'risk_distribution': {
                key: sum(row['risk'] == key for row in rows)
                for key in sorted({row['risk'] for row in rows})
            },
            'derived_image_bytes': sum(
                (staging_dir / row['relative_path']).stat().st_size for row in rows
            ),
            'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'manifest': 'manifest.csv',
        }
        (staging_dir / 'subset_report.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
        )
        os.replace(staging_dir, output_dir)
    except Exception:
        # Keep an incomplete staging tree visible for review; never delete data implicitly.
        raise
    return {**result, 'output_dir': str(output_dir)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--sample-report', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--sample-size', type=int, default=40)
    parser.add_argument('--seed', type=int, default=2026)
    args = parser.parse_args(argv)
    try:
        result = prepare_subset(
            args.archive,
            args.sample_report,
            args.output_dir,
            sample_size=args.sample_size,
            seed=args.seed,
        )
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
