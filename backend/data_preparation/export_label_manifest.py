"""Export selected AI Hub label metadata to a local CSV for archive inspection."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

FIELDS = (
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
)


def _code(value: Any) -> str:
    if value is None or isinstance(value, (dict, list, bool)):
        return ''
    return str(value)


def _annotations(data: dict[str, Any]) -> list[dict[str, Any]]:
    value = data.get('annotations', data.get('annotation'))
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise ValueError('expected annotation(s) object or list')


def export_manifest(
    label_root: Path, output: Path, *, crop: str, task: str, disease: str
) -> dict[str, int]:
    """Write only selected-class metadata; source JSON files are never changed."""
    label_root = label_root.resolve()
    if not label_root.is_dir():
        raise ValueError(f'label root is not a directory: {label_root}')
    selected: list[dict[str, str]] = []
    json_count = 0
    error_count = 0
    for label_path in sorted(label_root.rglob('*.json')):
        json_count += 1
        try:
            data = json.loads(label_path.read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict) or not isinstance(data.get('description'), dict):
                raise ValueError('expected a JSON object with description')
            description = data['description']
            for annotation in _annotations(data):
                if (
                    _code(annotation.get('crop')),
                    _code(description.get('task')),
                    _code(annotation.get('disease')),
                ) != (str(crop), str(task), str(disease)):
                    continue
                image_ref = description.get('image')
                if not isinstance(image_ref, str) or not image_ref.strip():
                    raise ValueError('target label is missing description.image')
                selected.append(
                    {
                        'image_ref': image_ref,
                        'crop': _code(annotation.get('crop')),
                        'task': _code(description.get('task')),
                        'disease': _code(annotation.get('disease')),
                        'risk': _code(annotation.get('risk')),
                        'grow': _code(annotation.get('grow')),
                        'area': _code(annotation.get('area')),
                        'date': _code(description.get('date')),
                        'time': _code(description.get('time')),
                        'width': _code(description.get('width')),
                        'height': _code(description.get('height')),
                    }
                )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            error_count += 1

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(selected, key=lambda item: item['image_ref'].casefold()))
    return {'json_files_seen': json_count, 'target_rows': len(selected), 'error_count': error_count}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label-root', required=True, type=Path)
    parser.add_argument(
        '--output',
        required=True,
        type=Path,
        help='CSV contains original image filenames; write to a Git-ignored local path',
    )
    parser.add_argument('--crop', required=True)
    parser.add_argument('--task', required=True)
    parser.add_argument('--disease', required=True)
    args = parser.parse_args(argv)
    try:
        result = export_manifest(
            args.label_root, args.output, crop=args.crop, task=args.task, disease=args.disease
        )
    except (OSError, ValueError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps({**result, 'output': str(args.output)}, ensure_ascii=False))
    return 1 if result['error_count'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
