"""Inspect AI Hub 525 images and JSON without modifying source data."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator

from PIL import Image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
MAX_ERROR_DETAILS = 100


def _walk_files(root: Path) -> Iterator[Path]:
    """Yield paths incrementally instead of retaining a complete tree listing."""
    for directory, _, filenames in os.walk(root, followlinks=False):
        for filename in filenames:
            yield Path(directory) / filename


def _counter_dict(counter: collections.Counter) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter, key=str)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_dataset(root: Path | None = None, progress_every: int = 10000,
                    compute_hashes: bool = True, *, image_root: Path | None = None,
                    label_root: Path | None = None) -> dict[str, Any]:
    """Return aggregate integrity data with a disk-backed image index.

    Use ``root`` for a unified tree, or pass separate image and label roots to
    inspect archives that are intentionally stored in different locations.
    """
    if (image_root is None) != (label_root is None):
        raise ValueError("image_root and label_root must be provided together")
    if image_root is not None and root is not None:
        raise ValueError("use root or separate image_root/label_root, not both")
    if image_root is None:
        if root is None:
            raise ValueError("a dataset root or both separate roots are required")
        root = root.resolve()
        image_root = label_root = root
        report_root_name = root.name
    else:
        image_root = image_root.resolve()
        label_root = label_root.resolve()
        report_root_name = f"{image_root.name} + {label_root.name}"
    if not image_root.is_dir():
        raise ValueError(f"Image root is not a directory: {image_root}")
    if not label_root.is_dir():
        raise ValueError(f"Label root is not a directory: {label_root}")
    if progress_every < 0:
        raise ValueError("progress_every must be zero or greater")

    schema: collections.Counter[str] = collections.Counter()
    distributions = {name: collections.Counter() for name in
                     ("crop", "disease", "task", "risk", "area", "grow")}
    bbox_counts: collections.Counter[str] = collections.Counter()
    part_counts: collections.Counter[str] = collections.Counter()
    image_dimensions: collections.Counter[str] = collections.Counter()
    errors: list[dict[str, str]] = []
    corrupt_images: list[dict[str, str]] = []
    counts = collections.Counter({key: 0 for key in
                                  ("files", "images", "json", "parsed_json", "paired_json_to_image",
                                   "json_errors", "corrupt_images", "hash_errors")})
    boxes_outside = image_size_mismatches = 0
    hash_duplicate_files = None
    hash_unique = None

    def add_error(path: Path, base: Path, message: str) -> None:
        counts["json_errors"] += 1
        if len(errors) < MAX_ERROR_DETAILS:
            errors.append({"file": path.relative_to(base).as_posix(), "error": message})

    with tempfile.TemporaryDirectory(prefix="farm-data-audit-") as temp_dir:
        db = sqlite3.connect(Path(temp_dir) / "index.sqlite3")
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA synchronous=OFF")
        db.execute("PRAGMA cache_size=-8192")
        db.execute("PRAGMA temp_store=FILE")
        db.execute("CREATE TABLE images (name TEXT NOT NULL, stem TEXT NOT NULL, path TEXT NOT NULL, digest TEXT)")
        db.execute("CREATE INDEX image_name_idx ON images(name)")
        db.execute("CREATE INDEX image_stem_idx ON images(stem)")

        # First pass: validate each image and build a small-memory, disk-backed index.
        for path in _walk_files(image_root):
            counts["files"] += 1
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            counts["images"] += 1
            digest = None
            if compute_hashes:
                try:
                    digest = _sha256(path)
                except OSError as exc:
                    counts["hash_errors"] += 1
            try:
                with Image.open(path) as image:
                    image_dimensions[f"{image.format}:{image.width}x{image.height}"] += 1
                    image.verify()
            except (OSError, ValueError) as exc:
                counts["corrupt_images"] += 1
                if len(corrupt_images) < MAX_ERROR_DETAILS:
                    corrupt_images.append({"file": path.relative_to(image_root).as_posix(), "error": str(exc)})
            db.execute("INSERT INTO images VALUES (?, ?, ?, ?)",
                       (path.name.casefold(), path.stem.casefold(), str(path), digest))
            if progress_every and counts["images"] % progress_every == 0:
                print(f"[images] {counts['images']:,} scanned", file=sys.stderr, flush=True)

        db.commit()
        db.execute("CREATE TABLE label_refs (name TEXT NOT NULL, stem TEXT NOT NULL)")

        # Second pass: parse one label at a time; only aggregate counters are retained.
        for label_path in _walk_files(label_root):
            if label_root != image_root:
                counts["files"] += 1
            if label_path.suffix.lower() != ".json":
                continue
            counts["json"] += 1
            try:
                data = json.loads(label_path.read_text(encoding="utf-8-sig"))
                if not isinstance(data, dict):
                    raise ValueError("JSON root must be an object")
                counts["parsed_json"] += 1
                description = data.get("description")
                annotation = data.get("annotations", data.get("annotation"))
                if not isinstance(description, dict) or not isinstance(annotation, dict):
                    raise ValueError("expected description and annotation(s) objects")

                for section_name, section in (("description", description), ("annotation", annotation)):
                    for key, value in section.items():
                        schema[f"{section_name}.{key}:{type(value).__name__}"] += 1
                for field in ("crop", "disease", "risk", "area", "grow"):
                    if field in annotation:
                        distributions[field][str(annotation[field])] += 1
                if "task" in description:
                    distributions["task"][str(description["task"])] += 1

                target_name = description.get("image")
                matches = []
                if not isinstance(target_name, str) or not target_name:
                    add_error(label_path, label_root, "missing description.image")
                else:
                    target_key = target_name.casefold()
                    target_stem = Path(target_name).stem.casefold()
                    db.execute("INSERT INTO label_refs VALUES (?, ?)", (target_key, target_stem))
                    matches = db.execute("SELECT path FROM images WHERE name=? LIMIT 2", (target_key,)).fetchall()
                    counts["paired_json_to_image"] += len(matches) == 1
                    if len(matches) == 1:
                        try:
                            with Image.open(matches[0][0]) as image:
                                if (description.get("width"), description.get("height")) != image.size:
                                    image_size_mismatches += 1
                        except (OSError, ValueError):
                            pass

                width, height = description.get("width"), description.get("height")
                valid_size = (isinstance(width, (int, float)) and isinstance(height, (int, float))
                              and width > 0 and height > 0)
                for kind, box_counter in (("bbox", bbox_counts), ("part", part_counts)):
                    boxes = annotation.get(kind, [])
                    if boxes is None and kind == "part":
                        boxes = []
                    if not isinstance(boxes, list):
                        add_error(label_path, label_root, f"{kind} must be a list")
                        continue
                    box_counter[str(len(boxes))] += 1
                    for index, box in enumerate(boxes):
                        if not isinstance(box, dict) or not all(k in box for k in ("x", "y", "w", "h")):
                            add_error(label_path, label_root, f"invalid {kind}[{index}]")
                            continue
                        try:
                            x, y, box_w, box_h = (float(box[k]) for k in ("x", "y", "w", "h"))
                            if min(x, y, box_w, box_h) < 0 or box_w <= 0 or box_h <= 0:
                                raise ValueError
                            if valid_size and (x + box_w > width + 1 or y + box_h > height + 1):
                                boxes_outside += 1
                        except (TypeError, ValueError):
                            add_error(label_path, label_root, f"invalid coordinates in {kind}[{index}]")
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                add_error(label_path, label_root, str(exc))
            if progress_every and counts["json"] % progress_every == 0:
                print(f"[json] {counts['json']:,} scanned", file=sys.stderr, flush=True)

        db.commit()
        counts["json_without_image"] = db.execute(
            "SELECT COUNT(*) FROM label_refs r WHERE NOT EXISTS "
            "(SELECT 1 FROM images i WHERE i.name=r.name)"
        ).fetchone()[0]
        counts["image_without_json_by_filename"] = db.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT stem FROM images i WHERE NOT EXISTS "
            "(SELECT 1 FROM label_refs r WHERE r.stem=i.stem))"
        ).fetchone()[0]
        counts["duplicate_image_filenames"] = db.execute(
            "SELECT COUNT(*) FROM (SELECT name FROM images GROUP BY name HAVING COUNT(*)>1)"
        ).fetchone()[0]
        counts["duplicate_json_image_references"] = db.execute(
            "SELECT COUNT(*) FROM (SELECT name FROM label_refs GROUP BY name HAVING COUNT(*)>1)"
        ).fetchone()[0]
        if compute_hashes:
            duplicate_counts = db.execute(
                "SELECT COALESCE(SUM(n-1), 0), COUNT(*) FROM "
                "(SELECT digest, COUNT(*) AS n FROM images WHERE digest IS NOT NULL GROUP BY digest)"
            ).fetchone()
            hash_duplicate_files, hash_unique = duplicate_counts
        db.close()

    counts["image_size_mismatches"] = image_size_mismatches
    return {
        "root_name": report_root_name,
        "image_root_name": image_root.name,
        "label_root_name": label_root.name,
        "counts": dict(counts),
        "image_dimensions": _counter_dict(image_dimensions),
        "schema_fields": _counter_dict(schema),
        "source_code_distributions": {name: _counter_dict(counter) for name, counter in distributions.items()},
        "bbox_count_per_json": _counter_dict(bbox_counts),
        "part_count_per_json": _counter_dict(part_counts),
        "boxes_outside_declared_image": boxes_outside,
        "image_size_mismatches": image_size_mismatches,
        "sha256_duplicate_files": hash_duplicate_files,
        "sha256_unique_images": hash_unique,
        "hashes_computed": compute_hashes,
        "json_errors": errors,
        "json_error_details_truncated": counts["json_errors"] > len(errors),
        "corrupt_images_detail": corrupt_images,
        "corrupt_image_details_truncated": counts["corrupt_images"] > len(corrupt_images),
        "interpretation": {
            "class_name_mapping": "not performed; provide and review the official codebook first",
            "source_files_modified": False,
            "split_generated": False,
            "training_performed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    roots = parser.add_mutually_exclusive_group()
    roots.add_argument("--data-root", type=Path,
                       help="Unified tree containing images and JSON labels")
    roots.add_argument("--image-root", type=Path,
                       help="Image directory (use with --label-root)")
    parser.add_argument("--label-root", type=Path,
                        help="JSON label directory; required with --image-root")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument("--progress-every", type=int, default=10000,
                        help="Print image/JSON progress every N files (0 disables progress)")
    parser.add_argument("--skip-hashes", action="store_true",
                        help="Skip the full-file SHA-256 duplicate scan")
    args = parser.parse_args(argv)
    if args.progress_every < 0:
        parser.error("--progress-every must be zero or greater")
    if args.data_root is None and (args.image_root is None or args.label_root is None):
        parser.error("provide --data-root or both --image-root and --label-root")
    if args.data_root is not None and args.label_root is not None:
        parser.error("--label-root is only used with --image-root")
    try:
        report = inspect_dataset(
            args.data_root, args.progress_every, not args.skip_hashes,
            image_root=args.image_root, label_root=args.label_root,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if (report["counts"].get("json_errors", 0) or report["counts"].get("corrupt_images", 0)
                 or report["counts"].get("hash_errors", 0) or report["boxes_outside_declared_image"]
                 or report["counts"]["image_size_mismatches"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
