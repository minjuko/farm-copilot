"""Assign whole, externally verified groups to train/val/test deterministically."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

from model_training.dataset import CLASS_MAP, REQUIRED_FIELDS, load_class_map


def split_manifest(
    input_path: Path,
    output_path: Path,
    *,
    seed: int = 2026,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    class_map: dict[int, dict[str, str]] | None = None,
) -> dict:
    class_map = class_map or CLASS_MAP
    ratios = {'train': train_ratio, 'val': val_ratio, 'test': test_ratio}
    if any(value <= 0 for value in ratios.values()) or abs(sum(ratios.values()) - 1) > 1e-8:
        raise ValueError('split ratios must be positive and sum to 1')
    input_path, output_path = input_path.resolve(), output_path.resolve()
    if not input_path.is_file() or output_path.exists():
        raise ValueError('input must exist and output must not exist')
    with input_path.open('r', newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED_FIELDS.issubset(reader.fieldnames):
            raise ValueError('manifest is missing required columns')
        rows = list(reader)
        fields = list(reader.fieldnames)
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    source_hashes: set[str] = set()
    for line, row in enumerate(rows, start=2):
        group = row['group_id'].strip()
        if not group:
            raise ValueError(f'missing verified group_id at row {line}')
        evidence = row['group_evidence'].strip().casefold()
        if not evidence or 'unknown' in evidence or 'unverified' in evidence:
            raise ValueError(f'group_id lacks verified evidence at row {line}')
        try:
            class_id = int(row['class_id'])
        except (TypeError, ValueError) as exc:
            raise ValueError(f'invalid class_id at row {line}') from exc
        if class_id not in class_map:
            raise ValueError(f'unsupported class_id at row {line}')
        expected = class_map[class_id]
        if row['class_name'] != expected['name'] or any(
            row[field] != expected[field] for field in ('crop', 'task', 'disease')
        ):
            raise ValueError(f'class mapping/code mismatch at row {line}')
        if (
            row['dataset_key'] != '525'
            or not row['dataset_version'].strip()
            or not row['file_key'].strip()
        ):
            raise ValueError(f'missing dataset provenance at row {line}')
        source_hash = row['source_sha256'].lower()
        derived_hash = row['derived_sha256'].lower()
        if (
            len(source_hash) != 64
            or len(derived_hash) != 64
            or any(char not in '0123456789abcdef' for char in source_hash + derived_hash)
        ):
            raise ValueError(f'invalid image hash at row {line}')
        if source_hash in source_hashes:
            raise ValueError(f'duplicate source image hash at row {line}')
        source_hashes.add(source_hash)
        groups[group].append(row)
    if not groups:
        raise ValueError('manifest is empty')

    buckets: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for group, group_rows in groups.items():
        signature = tuple(sorted({int(row['class_id']) for row in group_rows}))
        buckets[signature].append(group)
    rng = random.Random(seed)
    assignments: dict[str, str] = {}
    for signature, bucket_groups in sorted(buckets.items()):
        rng.shuffle(bucket_groups)
        count = len(bucket_groups)
        if count < 3:
            raise ValueError(
                f'group pattern {signature} has only {count} groups; need at least 3 to populate all splits'
            )
        # Largest-remainder allocation while preserving at least one group per split.
        exact = {split: count * ratio for split, ratio in ratios.items()}
        allocation = {split: max(1, int(exact[split])) for split in ratios}
        while sum(allocation.values()) > count:
            choices = [split for split in ratios if allocation[split] > 1]
            target = max(choices, key=lambda split: allocation[split] - exact[split])
            allocation[target] -= 1
        while sum(allocation.values()) < count:
            target = max(ratios, key=lambda split: exact[split] - allocation[split])
            allocation[target] += 1
        cursor = 0
        for split in ratios:
            for group in bucket_groups[cursor : cursor + allocation[split]]:
                assignments[group] = split
            cursor += allocation[split]

    counts = {split: set() for split in ratios}
    for row in rows:
        counts[assignments[row['group_id'].strip()]].add(int(row['class_id']))
    expected_classes = set(class_map)
    if any(found != expected_classes for found in counts.values()):
        raise ValueError('group allocation cannot place all configured classes in every split')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('x', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            row['split'] = assignments[row['group_id'].strip()]
            writer.writerow(row)
    return {
        'rows': len(rows),
        'groups': len(groups),
        'seed': seed,
        'ratios': ratios,
        'group_counts': {
            split: sum(value == split for value in assignments.values()) for split in ratios
        },
        'class_counts': {
            split: {
                str(class_id): sum(
                    int(row['class_id']) == class_id
                    and assignments[row['group_id'].strip()] == split
                    for row in rows
                )
                for class_id in sorted(class_map)
            }
            for split in ratios
        },
        'output': str(output_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--train-ratio', type=float, default=0.70)
    parser.add_argument('--val-ratio', type=float, default=0.15)
    parser.add_argument('--test-ratio', type=float, default=0.15)
    parser.add_argument('--class-config', type=Path, help='JSON class contract; defaults to legacy 3-class')
    args = parser.parse_args(argv)
    try:
        report = split_manifest(
            args.input,
            args.output,
            seed=args.seed,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            class_map=load_class_map(args.class_config),
        )
    except (OSError, ValueError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
