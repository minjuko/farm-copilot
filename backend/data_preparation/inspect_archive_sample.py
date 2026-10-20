"""Stream and inspect a reproducible, stratified sample from an image ZIP."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import random
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, UnidentifiedImageError

IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
MAX_ERRORS = 25


def _code(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list, bool)):
        return None
    return str(value)


def _annotations(data: dict[str, Any]) -> list[dict[str, Any]]:
    value = data.get('annotations', data.get('annotation'))
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise ValueError('expected annotation(s) object or list')


def _image_basename(reference: str) -> str:
    return PurePosixPath(reference.replace('\\', '/')).name.casefold()


def _label_record(description: dict[str, Any], annotation: dict[str, Any]) -> dict[str, Any]:
    image_ref = description.get('image')
    if not isinstance(image_ref, str) or not image_ref.strip():
        raise ValueError('target label is missing description.image')

    def dimension(value: Any) -> Any:
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    return {
        'image_ref': image_ref,
        'basename': _image_basename(image_ref),
        'risk': _code(annotation.get('risk')),
        'grow': _code(annotation.get('grow')),
        'area': _code(annotation.get('area')),
        'date': _code(description.get('date')),
        'time': _code(description.get('time')),
        'declared_width': dimension(description.get('width')),
        'declared_height': dimension(description.get('height')),
    }


def _quotas(groups: dict[str, list[dict[str, Any]]], count: int) -> dict[str, int]:
    """Allocate a fixed count proportionally using deterministic largest remainders."""
    count = min(count, sum(len(items) for items in groups.values()))
    quotas = {key: 0 for key in groups}
    remaining = count
    while remaining:
        eligible = [key for key, items in groups.items() if quotas[key] < len(items)]
        if not eligible:
            break
        total = sum(len(groups[key]) - quotas[key] for key in eligible)
        exact = {key: remaining * (len(groups[key]) - quotas[key]) / total for key in eligible}
        floors = {key: min(len(groups[key]) - quotas[key], int(exact[key])) for key in eligible}
        allocated = sum(floors.values())
        for key, amount in floors.items():
            quotas[key] += amount
        remaining -= allocated
        if not remaining:
            break
        ranked = sorted(
            (key for key in eligible if quotas[key] < len(groups[key])),
            key=lambda key: (-(exact[key] - int(exact[key])), key),
        )
        for key in ranked[:remaining]:
            quotas[key] += 1
        remaining -= min(remaining, len(ranked))
    return quotas


def _sample(records: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    """Balance risk codes, then proportionally stratify on metadata within risk."""
    if sample_size <= 0:
        raise ValueError('sample_size must be greater than zero')
    rng = random.Random(seed)
    by_risk: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for record in records:
        by_risk[record['risk'] or 'unknown'].append(record)
    if not by_risk:
        return []

    risks = sorted(by_risk)
    target = min(sample_size, len(records))
    risk_quota = {risk: 0 for risk in risks}
    # Round-robin risk allocation keeps rare risk codes represented.
    while sum(risk_quota.values()) < target:
        for risk in risks:
            if risk_quota[risk] < len(by_risk[risk]) and sum(risk_quota.values()) < target:
                risk_quota[risk] += 1

    selected: list[dict[str, Any]] = []
    for risk in risks:
        risk_records = by_risk[risk]
        strata: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for record in risk_records:
            # Date month and declared size help spread the sample without
            # treating either field as a proven plant/group identifier.
            key = '|'.join(
                (
                    record['grow'] or 'unknown',
                    record['area'] or 'unknown',
                    (record['date'] or 'unknown')[:6],
                    f'{record["declared_width"]}x{record["declared_height"]}',
                )
            )
            strata[key].append(record)
        quotas = _quotas(strata, risk_quota[risk])
        for key in sorted(strata):
            group = sorted(strata[key], key=lambda item: item['image_ref'].casefold())
            selected.extend(rng.sample(group, quotas[key]))
    return sorted(selected, key=lambda item: item['image_ref'].casefold())


def _sha256_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    with archive.open(member, 'r') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _difference_hash(image: Image.Image) -> int:
    gray = image.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | (gray.getpixel((x, y)) > gray.getpixel((x + 1, y)))
    return value


def _extension_matches(extension: str, image_format: str) -> bool:
    expected = (
        'jpeg'
        if extension.lower().lstrip('.') in {'jpg', 'jpeg'}
        else extension.lower().lstrip('.')
    )
    actual = image_format.lower()
    # MPO is a JPEG-based container that Pillow reports separately.
    return actual in ({'jpeg', 'mpo'} if expected == 'jpeg' else {expected})


def _counter(counter: collections.Counter) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter, key=str)}


def inspect_archive_sample(
    archive_path: Path,
    label_root: Path | None = None,
    *,
    label_manifest: Path | None = None,
    crop: str,
    task: str,
    disease: str,
    sample_size: int = 200,
    seed: int = 2026,
    metadata_encoding: str = 'cp949',
) -> dict[str, Any]:
    """Pair class-specific TL1 labels with ZIP members and decode a small sample.

    Image bytes are read directly from the ZIP. No source image is extracted or
    written. The returned sample manifest contains image filenames and should
    be saved only under a Git-ignored local directory.
    """
    archive_path = archive_path.resolve()
    if not archive_path.is_file():
        raise ValueError(f'image archive is not a file: {archive_path}')
    if (label_root is None) == (label_manifest is None):
        raise ValueError('provide exactly one of label_root or label_manifest')
    if label_root is not None:
        label_root = label_root.resolve()
        if not label_root.is_dir():
            raise ValueError(f'label root is not a directory: {label_root}')
        label_source_kind = 'json_directory'
        label_source_path = label_root
    else:
        assert label_manifest is not None
        label_manifest = label_manifest.resolve()
        if not label_manifest.is_file():
            raise ValueError(f'label manifest is not a file: {label_manifest}')
        label_source_kind = 'csv_manifest'
        label_source_path = label_manifest
    if sample_size <= 0:
        raise ValueError('sample_size must be greater than zero')

    label_records: list[dict[str, Any]] = []
    label_errors: list[dict[str, str]] = []
    label_error_count = 0
    json_count = 0
    class_codes = (str(crop), str(task), str(disease))
    seen_refs: collections.Counter[str] = collections.Counter()
    if label_root is not None:
        for label_path in sorted(label_root.rglob('*.json')):
            json_count += 1
            try:
                data = json.loads(label_path.read_text(encoding='utf-8-sig'))
                if not isinstance(data, dict) or not isinstance(data.get('description'), dict):
                    raise ValueError('expected a JSON object with description')
                description = data['description']
                for annotation in _annotations(data):
                    candidate = (
                        _code(annotation.get('crop')),
                        _code(description.get('task')),
                        _code(annotation.get('disease')),
                    )
                    if candidate == class_codes:
                        label_records.append(_label_record(description, annotation))
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                label_error_count += 1
                if len(label_errors) < MAX_ERRORS:
                    label_errors.append({'file': label_path.name, 'error': str(exc)})
    else:
        assert label_manifest is not None
        required_fields = {
            'image_ref',
            'crop',
            'task',
            'disease',
            'risk',
            'grow',
            'area',
            'date',
            'time',
            'width',
            'height',
        }
        try:
            with label_manifest.open('r', newline='', encoding='utf-8-sig') as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames or not required_fields.issubset(reader.fieldnames):
                    raise ValueError('label manifest is missing required columns')
                for row in reader:
                    json_count += 1
                    if (row.get('crop'), row.get('task'), row.get('disease')) != class_codes:
                        continue
                    description = {
                        'image': row.get('image_ref'),
                        'task': row.get('task'),
                        'date': row.get('date'),
                        'time': row.get('time'),
                        'width': row.get('width'),
                        'height': row.get('height'),
                    }
                    annotation = {
                        'crop': row.get('crop'),
                        'disease': row.get('disease'),
                        'risk': row.get('risk'),
                        'grow': row.get('grow'),
                        'area': row.get('area'),
                    }
                    label_records.append(_label_record(description, annotation))
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            label_error_count += 1
            label_errors.append({'file': label_manifest.name, 'error': str(exc)})

    for record in label_records:
        seen_refs[record['basename']] += 1

    try:
        archive = zipfile.ZipFile(archive_path, metadata_encoding=metadata_encoding)
    except TypeError:  # Python < 3.11 does not support metadata_encoding.
        archive = zipfile.ZipFile(archive_path)
    with archive:
        infos = [
            info
            for info in archive.infolist()
            if not info.is_dir() and PurePosixPath(info.filename).suffix.lower() in IMAGE_SUFFIXES
        ]
        by_basename: dict[str, list[zipfile.ZipInfo]] = collections.defaultdict(list)
        for info in infos:
            by_basename[PurePosixPath(info.filename).name.casefold()].append(info)
        duplicate_archive_names = sum(len(items) > 1 for items in by_basename.values())

        paired: list[dict[str, Any]] = []
        missing_refs = 0
        ambiguous_refs = 0
        for record in label_records:
            matches = by_basename.get(record['basename'], [])
            if len(matches) == 1:
                paired.append({**record, 'zip_member': matches[0]})
            elif not matches:
                missing_refs += 1
            else:
                ambiguous_refs += 1

        # A duplicate TL1 reference must not inflate the available sample pool.
        unique: dict[str, dict[str, Any]] = {}
        for record in paired:
            unique.setdefault(record['basename'], record)
        paired_unique = list(unique.values())
        selected = _sample(paired_unique, sample_size, seed)

        formats: collections.Counter[str] = collections.Counter()
        modes: collections.Counter[str] = collections.Counter()
        dimensions: collections.Counter[str] = collections.Counter()
        orientations: collections.Counter[str] = collections.Counter()
        size_mismatches = 0
        extension_mismatches = 0
        decode_errors: list[dict[str, str]] = []
        decode_error_count = 0
        hashes: collections.Counter[str] = collections.Counter()
        dhashes: list[tuple[int, str]] = []
        selected_rows: list[dict[str, Any]] = []

        for record in selected:
            info = record['zip_member']
            digest = _sha256_member(archive, info)
            hashes[digest] += 1
            image_format = 'unknown'
            image_mode = 'unknown'
            width = height = None
            orientation = None
            dhash = None
            try:
                with archive.open(info, 'r') as stream:
                    with Image.open(stream) as image:
                        image_format = image.format or 'unknown'
                        image_mode = image.mode
                        width, height = image.size
                        exif = image.getexif()
                        orientation = exif.get(274)
                        image.verify()
                with archive.open(info, 'r') as stream:
                    with Image.open(stream) as image:
                        image.load()
                        dhash = _difference_hash(image)
            except (
                OSError,
                ValueError,
                SyntaxError,
                UnidentifiedImageError,
                zipfile.BadZipFile,
            ) as exc:
                decode_error_count += 1
                if len(decode_errors) < MAX_ERRORS:
                    decode_errors.append({'image_ref': record['image_ref'], 'error': str(exc)})

            formats[image_format] += 1
            modes[image_mode] += 1
            if width is not None and height is not None:
                dimensions[f'{width}x{height}'] += 1
                if (record['declared_width'], record['declared_height']) != (width, height):
                    size_mismatches += 1
            ext = PurePosixPath(record['image_ref']).suffix.lower().lstrip('.')
            if ext and not _extension_matches(ext, image_format):
                extension_mismatches += 1
            orientations[str(orientation) if orientation is not None else 'absent'] += 1
            if dhash is not None:
                dhashes.append((dhash, record['image_ref']))
            selected_rows.append(
                {
                    'image_ref': record['image_ref'],
                    'risk': record['risk'],
                    'grow': record['grow'],
                    'area': record['area'],
                    'date': record['date'],
                    'time': record['time'],
                    'zip_member_size': info.file_size,
                    'actual_format': image_format,
                    'actual_mode': image_mode,
                    'actual_dimensions': [width, height] if width is not None else None,
                    'declared_dimensions': [record['declared_width'], record['declared_height']],
                    'exif_orientation': orientation,
                    'sha256': digest,
                }
            )

        exact_duplicate_extras = sum(amount - 1 for amount in hashes.values() if amount > 1)
        near_duplicate_pairs = 0
        for index, (left, _) in enumerate(dhashes):
            for right, _ in dhashes[index + 1 :]:
                if (left ^ right).bit_count() <= 4:
                    near_duplicate_pairs += 1

        return {
            'archive': {
                'name': archive_path.name,
                'size_bytes': archive_path.stat().st_size,
                'image_members': len(infos),
                'duplicate_image_basenames': duplicate_archive_names,
            },
            'labels': {
                'json_files_seen': json_count,
                'input_kind': label_source_kind,
                'input_path': str(label_source_path),
                'target_codes': {'crop': crop, 'task': task, 'disease': disease},
                'target_rows': len(label_records),
                'target_unique_image_refs': len(seen_refs),
                'duplicate_target_refs': sum(
                    amount - 1 for amount in seen_refs.values() if amount > 1
                ),
                'paired_unique_refs': len(paired_unique),
                'missing_refs': missing_refs,
                'ambiguous_refs': ambiguous_refs,
                'label_error_count': label_error_count,
                'label_errors': label_errors,
            },
            'sample': {
                'requested': sample_size,
                'selected': len(selected),
                'seed': seed,
                'policy': 'risk-balanced; proportional within risk by grow, area, date month, and declared dimensions',
                'risk_distribution': _counter(
                    collections.Counter(item['risk'] or 'unknown' for item in selected)
                ),
                'grow_distribution': _counter(
                    collections.Counter(item['grow'] or 'unknown' for item in selected)
                ),
                'area_distribution': _counter(
                    collections.Counter(item['area'] or 'unknown' for item in selected)
                ),
                'month_distribution': _counter(
                    collections.Counter((item['date'] or 'unknown')[:6] for item in selected)
                ),
                'date_range': [
                    min((item['date'] for item in selected if item['date']), default=None),
                    max((item['date'] for item in selected if item['date']), default=None),
                ],
                'decoded_images': len(selected) - decode_error_count,
                'decode_error_count': decode_error_count,
                'decode_errors': decode_errors,
                'actual_format_distribution': _counter(formats),
                'actual_mode_distribution': _counter(modes),
                'actual_dimensions_distribution': _counter(dimensions),
                'exif_orientation_distribution': _counter(orientations),
                'declared_dimension_mismatches': size_mismatches,
                'extension_format_mismatches': extension_mismatches,
                'exact_duplicate_extras_in_sample': exact_duplicate_extras,
                'dhash_pairs_at_distance_le_4': near_duplicate_pairs,
                'files': selected_rows,
            },
            'limitations': [
                'This is a reproducible sample, not a full-corpus image-quality estimate.',
                'Near-duplicate dHash pairs are review candidates, not proof of shared source plants or augmentation.',
                'TL1 filename pairing does not establish that the visible disease matches the label.',
                'Sample files in this report contain original image references; keep the report Git-ignored and local.',
            ],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--archive', required=True, type=Path, help='Source image ZIP; never extracted'
    )
    label_input = parser.add_mutually_exclusive_group(required=True)
    label_input.add_argument('--label-root', type=Path, help='TL1 JSON directory')
    label_input.add_argument(
        '--label-manifest',
        type=Path,
        help='CSV exported from WSL when Windows cannot read its Linux home',
    )
    parser.add_argument('--crop', required=True)
    parser.add_argument('--task', required=True)
    parser.add_argument('--disease', required=True)
    parser.add_argument('--sample-size', type=int, default=200)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument(
        '--output',
        required=True,
        type=Path,
        help='JSON output; contains image filenames, use a Git-ignored local path',
    )
    args = parser.parse_args(argv)
    try:
        report = inspect_archive_sample(
            args.archive,
            args.label_root,
            label_manifest=args.label_manifest,
            crop=args.crop,
            task=args.task,
            disease=args.disease,
            sample_size=args.sample_size,
            seed=args.seed,
        )
        if report['sample']['selected'] == 0:
            raise ValueError('no target images were paired between labels and archive')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    sample = report['sample']
    print(
        json.dumps(
            {
                'archive': report['archive'],
                'labels': {
                    key: value for key, value in report['labels'].items() if key != 'label_errors'
                },
                'sample': {
                    key: value
                    for key, value in sample.items()
                    if key != 'files' and key != 'decode_errors'
                },
                'decode_error_count': len(sample['decode_errors']),
                'report': str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if sample['decode_errors'] or sample['declared_dimension_mismatches'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
