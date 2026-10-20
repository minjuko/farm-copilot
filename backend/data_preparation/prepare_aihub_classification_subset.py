"""Extract a deterministic, label-matched subset from per-class AI Hub ZIPs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import sys
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare_subset(
    class_inputs: dict[str, tuple[Path, Path]],
    class_config_path: Path,
    output_dir: Path,
    *,
    sample_size: int = 100,
    seed: int = 2026,
) -> dict:
    """Match TL1 references against ZIP members and extract selected JPEG derivatives."""
    class_config_path, output_dir = class_config_path.resolve(), output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f'output directory already exists: {output_dir}')
    if not class_config_path.is_file():
        raise ValueError('class config must exist')
    config = json.loads(class_config_path.read_text(encoding='utf-8-sig'))
    class_rows = config.get('classes', [])
    if len(class_rows) < 2 or sample_size < 1:
        raise ValueError('class config must contain at least two classes and sample size must be positive')
    contracts = {str(row['name']): row for row in class_rows}
    if set(class_inputs) != set(contracts):
        raise ValueError('provide exactly one archive and label manifest for each configured class')

    candidates: dict[str, dict[str, dict[str, str]]] = {}
    for class_name, (archive_path, manifest_path) in class_inputs.items():
        archive_path = archive_path.resolve()
        if not archive_path.is_file():
            raise ValueError(f'archive does not exist: {archive_path}')
        if not manifest_path.is_file():
            raise ValueError(f'label manifest does not exist: {manifest_path}')
        with manifest_path.open('r', newline='', encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or not {'image_ref', 'crop', 'task', 'disease'}.issubset(reader.fieldnames):
                raise ValueError(f'invalid label manifest: {manifest_path}')
            rows = {}
            expected = contracts[class_name]
            for row in reader:
                codes = tuple(row.get(field, '') for field in ('crop', 'task', 'disease'))
                if codes != tuple(str(expected[key]) for key in ('crop', 'task', 'disease')):
                    continue
                ref = row['image_ref'].replace('\\', '/')
                if ref in rows:
                    raise ValueError(f'duplicate label image reference in {class_name}: {ref}')
                rows[ref] = row
        candidates[class_name] = rows
        class_inputs[class_name] = (archive_path, manifest_path.resolve())

    reference_owners: dict[str, str] = {}
    for class_name, rows in candidates.items():
        for image_ref in rows:
            key = image_ref.casefold()
            previous = reference_owners.setdefault(key, class_name)
            if previous != class_name:
                raise ValueError(f'image reference appears in multiple configured classes: {image_ref}')

    rng = random.Random(seed)
    selected: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for class_name, rows in candidates.items():
      archive_path, _ = class_inputs[class_name]
      with zipfile.ZipFile(archive_path, metadata_encoding='cp949') as archive:
        member_by_base: dict[str, list[str]] = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            base = PurePosixPath(info.filename.replace('\\', '/')).name.casefold()
            member_by_base.setdefault(base, []).append(info.filename)
        matches = []
        for ref, metadata in rows.items():
            members = member_by_base.get(PurePosixPath(ref).name.casefold(), [])
            if len(members) > 1:
                raise ValueError(f'ambiguous ZIP basename for TL1 reference: {ref}')
            if members:
                matches.append((members[0], metadata))
        if len(matches) < sample_size:
            raise ValueError(
                f'{class_name}: only {len(matches)} archive-matched labels; need {sample_size}'
            )
        selected[class_name] = sorted(rng.sample(matches, sample_size), key=lambda item: item[0].casefold())

    staging = output_dir.with_name(output_dir.name + '.staging')
    if staging.exists():
        raise ValueError(f'staging directory already exists: {staging}')
    staging.mkdir(parents=True)
    manifest_rows = []
    seen_source_hashes: set[str] = set()
    try:
      class_ids = {str(row['name']): int(row['class_id']) for row in class_rows}
      for class_name, members in selected.items():
        archive_path, _ = class_inputs[class_name]
        with zipfile.ZipFile(archive_path, metadata_encoding='cp949') as archive:
                image_dir = staging / 'images' / class_name
                image_dir.mkdir(parents=True)
                for member, metadata in members:
                    raw = archive.read(member)
                    source_hash = sha256(raw)
                    if source_hash in seen_source_hashes:
                        raise ValueError('selected subset contains byte-identical source images')
                    seen_source_hashes.add(source_hash)
                    with Image.open(io.BytesIO(raw)) as image:
                        image = ImageOps.exif_transpose(image).convert('RGB')
                        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
                        image.load()
                        relative = Path('images') / class_name / f'{source_hash[:16]}.jpg'
                        path = staging / relative
                        image.save(path, format='JPEG', quality=90, optimize=True)
                    derived_hash = sha256(path.read_bytes())
                    manifest_rows.append({
                        'relative_path': relative.as_posix(), 'split': 'unassigned',
                        'class_id': class_ids[class_name], 'class_name': class_name,
                        'crop': metadata['crop'], 'task': metadata['task'], 'disease': metadata['disease'],
                        'source_image_ref': metadata['image_ref'], 'source_member': member,
                        'source_file_key': str(contracts[class_name].get('file_key', '')),
                        'source_sha256': source_hash, 'derived_sha256': derived_hash,
                        'capture_date': metadata.get('date', ''), 'capture_time': metadata.get('time', ''),
                        'group_id': '', 'group_evidence': 'unknown; no plant identity verified',
                    })
      fields = list(manifest_rows[0])
      with (staging / 'manifest.csv').open('x', newline='', encoding='utf-8-sig') as stream:
          writer = csv.DictWriter(stream, fieldnames=fields)
          writer.writeheader()
          writer.writerows(manifest_rows)
      report = {
                'dataset_key': str(config.get('dataset_key', '')),
                'source_archives': {
                    name: {'name': class_inputs[name][0].name,
                           'size_bytes': class_inputs[name][0].stat().st_size,
                           'file_key': str(contracts[name].get('file_key', ''))}
                    for name in class_inputs
                },
                'seed': seed,
                'sample_size_per_class': sample_size,
                'class_counts': {name: len(rows) for name, rows in selected.items()},
                'split': 'unassigned; verified group metadata required before splitting/training',
                'transform': 'EXIF transpose; RGB; longest side <=768; JPEG quality=90',
                'manifest': 'manifest.csv',
      }
      (staging / 'subset_report.json').write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
      )
      staging.replace(output_dir)
    except Exception:
        raise
    return {**report, 'output_dir': str(output_dir)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--class-config', required=True, type=Path)
    parser.add_argument('--class-input', action='append', required=True, metavar='CLASS=ZIP=CSV')
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--sample-size', type=int, default=100)
    parser.add_argument('--seed', type=int, default=2026)
    args = parser.parse_args(argv)
    try:
        inputs = {}
        for value in args.class_input:
            parts = value.split('=', 2)
            if len(parts) != 3 or not all(parts) or parts[0] in inputs:
                raise ValueError('--class-input must be unique CLASS=ZIP=CSV values')
            inputs[parts[0]] = (Path(parts[1]), Path(parts[2]))
        result = prepare_subset(
            inputs, args.class_config, args.output_dir,
            sample_size=args.sample_size, seed=args.seed,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
