"""Analyze AI Hub 525 JSON labels without requiring the image archive."""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterator


TARGET_CLASSES = {
    "pepper_healthy": ("5", "0", "00"),
    "pepper_anthracnose": ("5", "1", "a7"),
    "pepper_powdery_mildew": ("5", "1", "a8"),
}
EXPECTED_TASK_FOR_DISEASE = {
    "00": "0",
    **{f"a{i}": "1" for i in range(1, 13)},
    **{f"b{i}": "2" for i in range(1, 9)},
    **{f"c{i}": "3" for i in (1, 2, 3, 4, 5, 6, 7, 9, 11, 12)},
}
MAX_ERROR_DETAILS = 100
FILENAME_DATE = re.compile(r"^\d{8}$")


def _walk_json(root: Path) -> Iterator[Path]:
    for directory, _, filenames in os.walk(root, followlinks=False):
        for filename in filenames:
            if filename.lower().endswith(".json"):
                yield Path(directory) / filename


def _counter_dict(counter: collections.Counter[str]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter, key=str)}


def _as_code(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list, bool)):
        return None
    return str(value)


def _annotations(data: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]]]:
    if "annotations" in data:
        key = "annotations"
    elif "annotation" in data:
        key = "annotation"
    else:
        return None, []
    value = data[key]
    if isinstance(value, dict):
        return key, [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return key, value
    raise ValueError(f"{key} must be an object or a list of objects")


def _filename_components(image_ref: str) -> dict[str, str] | None:
    """Decode the documented ten-component filename without assigning group meaning."""
    stem = PurePosixPath(image_ref.replace("\\", "/")).stem
    fields = stem.split("_")
    if len(fields) != 10 or not FILENAME_DATE.fullmatch(fields[1]):
        return None
    return {
        "date": fields[1],
        "crop": fields[2],
        "task": fields[3],
        "disease": fields[4],
        "area": fields[5],
        "grow": fields[7],
        "risk": fields[8],
        "capture_sequence": fields[9],
    }


def analyze_labels(root: Path, max_errors: int = MAX_ERROR_DETAILS) -> dict[str, Any]:
    """Aggregate label structure and code distributions without opening images."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Label root is not a directory: {root}")
    if max_errors < 0:
        raise ValueError("max_errors must be zero or greater")

    counts = collections.Counter({
        name: 0 for name in (
            "json_files", "parsed_json", "json_errors", "missing_description",
            "missing_annotations", "images_with_multiple_annotation_objects",
            "json_without_image_reference", "duplicate_image_reference_extras",
            "duplicate_image_reference_names", "image_references_with_multiple_classes",
            "filename_reference_has_directory", "filename_reference_has_windows_separator",
            "filename_pattern_matches", "filename_pattern_unrecognized",
            "filename_metadata_checks", "filename_metadata_mismatches",
            "bbox_objects", "bbox_invalid", "bbox_outside_declared_dimensions",
            "part_objects", "part_invalid",
        )
    })
    errors: list[dict[str, str]] = []
    schema: collections.Counter[str] = collections.Counter()
    distributions = {
        field: collections.Counter()
        for field in ("crop", "task", "disease", "risk", "grow", "area")
    }
    combinations: collections.Counter[tuple[str, str, str]] = collections.Counter()
    target_image_refs = {name: set() for name in TARGET_CLASSES}
    target_annotation_rows = collections.Counter({name: 0 for name in TARGET_CLASSES})
    bbox_counts: collections.Counter[str] = collections.Counter()
    part_counts: collections.Counter[str] = collections.Counter()
    dimension_counts: collections.Counter[str] = collections.Counter()
    date_counts: collections.Counter[str] = collections.Counter()
    time_counts: collections.Counter[str] = collections.Counter()
    region_counts: collections.Counter[str] = collections.Counter()
    filename_token_counts: collections.Counter[str] = collections.Counter()
    image_reference_counts: collections.Counter[str] = collections.Counter()
    image_ref_combinations: dict[str, set[tuple[str, str, str]]] = collections.defaultdict(set)
    task_disease_inconsistencies: collections.Counter[tuple[str, str, str]] = collections.Counter()
    filename_mismatches: collections.Counter[str] = collections.Counter()

    def add_error(path: Path, message: str) -> None:
        counts["json_errors"] += 1
        if len(errors) < max_errors:
            errors.append({"file": path.relative_to(root).as_posix(), "error": message})

    for label_path in _walk_json(root):
        counts["json_files"] += 1
        try:
            data = json.loads(label_path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("JSON root must be an object")
            counts["parsed_json"] += 1
            description = data.get("description")
            if not isinstance(description, dict):
                counts["missing_description"] += 1
                raise ValueError("description must be an object")
            annotations_key, annotation_rows = _annotations(data)
            if annotations_key is None:
                counts["missing_annotations"] += 1
                raise ValueError("missing annotation or annotations object")
            schema[f"{annotations_key}:{type(data[annotations_key]).__name__}"] += 1
            if len(annotation_rows) > 1:
                counts["images_with_multiple_annotation_objects"] += 1
            for key, value in description.items():
                schema[f"description.{key}:{type(value).__name__}"] += 1
            for row in annotation_rows:
                for key, value in row.items():
                    schema[f"annotation.{key}:{type(value).__name__}"] += 1

            image_ref = description.get("image")
            ref_key = None
            components = None
            if isinstance(image_ref, str) and image_ref.strip():
                ref_key = image_ref.replace("\\", "/").casefold()
                if image_reference_counts[ref_key] > 0:
                    counts["duplicate_image_reference_extras"] += 1
                image_reference_counts[ref_key] += 1
                if "/" in image_ref:
                    counts["filename_reference_has_directory"] += 1
                if "\\" in image_ref:
                    counts["filename_reference_has_windows_separator"] += 1
                components = _filename_components(image_ref)
                if components is None:
                    counts["filename_pattern_unrecognized"] += 1
                else:
                    counts["filename_pattern_matches"] += 1
                    filename_token_counts[components["capture_sequence"]] += 1
                    date = _as_code(description.get("date"))
                    if date is not None:
                        counts["filename_metadata_checks"] += 1
                        if date != components["date"]:
                            counts["filename_metadata_mismatches"] += 1
                            filename_mismatches["date"] += 1
            else:
                counts["json_without_image_reference"] += 1

            for field in ("date", "time", "region"):
                value = _as_code(description.get(field))
                if value is not None:
                    {"date": date_counts, "time": time_counts, "region": region_counts}[field][value] += 1
            width = description.get("width")
            height = description.get("height")
            valid_dimensions = (
                isinstance(width, (int, float)) and not isinstance(width, bool) and width > 0
                and isinstance(height, (int, float)) and not isinstance(height, bool) and height > 0
            )
            if valid_dimensions:
                dimension_counts[f"{width}x{height}"] += 1

            image_classes: set[str] = set()
            for row in annotation_rows:
                codes = {field: _as_code(row.get(field)) for field in ("crop", "disease", "risk", "grow", "area")}
                codes["task"] = _as_code(description.get("task"))
                if components is not None:
                    for field in ("crop", "task", "disease", "area", "grow", "risk"):
                        actual = codes.get(field)
                        if actual is not None:
                            counts["filename_metadata_checks"] += 1
                            filename_value = components[field]
                            # AI Hub's observed pepper filename convention writes
                            # the healthy disease code 00 as a single 0 token.
                            if field == "disease" and actual == "00" and filename_value == "0":
                                filename_value = actual
                            if actual != filename_value:
                                counts["filename_metadata_mismatches"] += 1
                                filename_mismatches[field] += 1
                for field, value in codes.items():
                    if value is not None:
                        distributions[field][value] += 1
                crop, task, disease = codes["crop"], codes["task"], codes["disease"]
                if crop is not None and task is not None and disease is not None:
                    combinations[(crop, task, disease)] += 1
                    if ref_key is not None:
                        image_ref_combinations[ref_key].add((crop, task, disease))
                    expected_task = EXPECTED_TASK_FOR_DISEASE.get(disease)
                    if expected_task is not None and task != expected_task:
                        task_disease_inconsistencies[(crop, task, disease)] += 1
                target_key = (crop, task, disease)
                for class_name, expected in TARGET_CLASSES.items():
                    if target_key == expected:
                        target_annotation_rows[class_name] += 1
                        image_classes.add(class_name)

                for field, aggregate, invalid_key, outside_key in (
                    ("bbox", bbox_counts, "bbox_invalid", "bbox_outside_declared_dimensions"),
                    ("part", part_counts, "part_invalid", None),
                ):
                    boxes = row.get(field, [])
                    if boxes is None and field == "part":
                        boxes = []
                    if not isinstance(boxes, list):
                        counts[invalid_key] += 1
                        add_error(label_path, f"{field} must be a list")
                        continue
                    aggregate[str(len(boxes))] += 1
                    for index, box in enumerate(boxes):
                        counts["bbox_objects" if field == "bbox" else "part_objects"] += 1
                        if not isinstance(box, dict) or not all(k in box for k in ("x", "y", "w", "h")):
                            counts[invalid_key] += 1
                            add_error(label_path, f"invalid {field}[{index}]")
                            continue
                        try:
                            x, y, box_w, box_h = (float(box[k]) for k in ("x", "y", "w", "h"))
                            if min(x, y, box_w, box_h) < 0 or box_w <= 0 or box_h <= 0:
                                raise ValueError
                            if valid_dimensions and (x + box_w > width + 1 or y + box_h > height + 1):
                                if outside_key:
                                    counts[outside_key] += 1
                        except (TypeError, ValueError):
                            counts[invalid_key] += 1
                            add_error(label_path, f"invalid coordinates in {field}[{index}]")
            if ref_key is not None:
                for class_name in image_classes:
                    target_image_refs[class_name].add(ref_key)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            add_error(label_path, str(exc))

    counts["duplicate_image_reference_names"] = sum(n > 1 for n in image_reference_counts.values())
    counts["image_references_with_multiple_classes"] = sum(
        len(code_combinations) > 1 for code_combinations in image_ref_combinations.values()
    )

    return {
        "label_root_name": root.name,
        "images_present_or_checked": False,
        "counts": dict(counts),
        "schema_fields": _counter_dict(schema),
        "source_code_distributions": {name: _counter_dict(counter) for name, counter in distributions.items()},
        "crop_task_disease_combinations": {
            "|".join(key): value for key, value in sorted(combinations.items())
        },
        "target_classes": {
            name: {
                "source_codes": {"crop": crop, "task": task, "disease": disease},
                "annotation_rows": target_annotation_rows[name],
                "unique_image_references": len(target_image_refs[name]),
            }
            for name, (crop, task, disease) in TARGET_CLASSES.items()
        },
        "task_disease_inconsistencies": {
            "|".join(key): value for key, value in sorted(task_disease_inconsistencies.items())
        },
        "filename_metadata_mismatches_by_field": _counter_dict(filename_mismatches),
        "bbox_count_per_annotation": _counter_dict(bbox_counts),
        "part_count_per_annotation": _counter_dict(part_counts),
        "declared_image_dimensions": _counter_dict(dimension_counts),
        "date_distribution": _counter_dict(date_counts),
        "time_distribution": _counter_dict(time_counts),
        "region_distribution": _counter_dict(region_counts),
        "capture_sequence_distribution": _counter_dict(filename_token_counts),
        "errors": errors,
        "error_details_truncated": counts["json_errors"] > len(errors),
        "limitations": [
            "Image existence, decoding, dimensions, hashes, and visual duplicates were not checked.",
            "Filename capture sequence is reported as a token only; it is not assumed to identify a plant or split group.",
            "Original-versus-augmented relationships are not inferred without an explicit source field or verified rule.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label-root", required=True, type=Path, help="Extracted label directory; images are optional")
    parser.add_argument("--output", type=Path, help="Optional JSON report path; existing files are not overwritten")
    args = parser.parse_args(argv)
    try:
        report = analyze_labels(args.label_root)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        except FileExistsError:
            print(f"error: output already exists: {args.output}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"error: cannot write output: {exc}", file=sys.stderr)
            return 2
    else:
        print(rendered, end="")
    failed_counts = report["counts"]
    has_code_inconsistencies = bool(report["task_disease_inconsistencies"])
    if (
        failed_counts["json_files"] == 0
        or failed_counts["json_errors"]
        or failed_counts["json_without_image_reference"]
        or failed_counts["duplicate_image_reference_extras"]
        or failed_counts["image_references_with_multiple_classes"]
        or failed_counts["filename_metadata_mismatches"]
        or failed_counts["bbox_invalid"]
        or failed_counts["bbox_outside_declared_dimensions"]
        or failed_counts["part_invalid"]
        or has_code_inconsistencies
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
