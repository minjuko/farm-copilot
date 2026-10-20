import json
import tempfile
import unittest
from pathlib import Path

from data_preparation.analyze_label_archive import analyze_labels, main


class AnalyzeLabelArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "labels"
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_label(self, filename, *, crop=5, task=1, disease="a7", image=None,
                    annotation_key="annotations", annotation_overrides=None,
                    description_overrides=None):
        image = image or filename.removesuffix(".json") + ".JPG"
        annotation = {
            "crop": crop,
            "disease": disease,
            "risk": 2,
            "grow": 13,
            "area": 1,
            "bbox": [{"x": 2, "y": 3, "w": 4, "h": 5}],
            "part": [],
        }
        annotation.update(annotation_overrides or {})
        description = {
            "image": image,
            "date": "20210802",
            "time": "1401",
            "region": 0,
            "width": 100,
            "height": 80,
            "task": task,
        }
        description.update(description_overrides or {})
        (self.root / filename).write_text(
            json.dumps({"description": description, annotation_key: annotation}), encoding="utf-8"
        )

    def test_analyzes_target_classes_without_images(self):
        self.write_label("healthy.json", crop=5, task=0, disease="00",
                         image="100_20210802_5_0_0_1_2_13_0_0.JPG",
                         annotation_overrides={"risk": 0})
        self.write_label("anthracnose.json", crop=5, task=1, disease="a7",
                         image="101_20210802_5_1_a7_1_2_13_2_0.JPG")
        self.write_label("powdery.json", crop=5, task=1, disease="a8",
                         image="102_20210802_5_1_a8_1_2_13_2_0.JPG",
                         annotation_key="annotation")

        report = analyze_labels(self.root)

        self.assertFalse(report["images_present_or_checked"])
        self.assertEqual(report["counts"]["json_files"], 3)
        self.assertEqual(report["counts"]["parsed_json"], 3)
        self.assertEqual(report["counts"]["json_errors"], 0)
        self.assertEqual(report["counts"]["filename_metadata_mismatches"], 0)
        self.assertEqual(report["target_classes"]["pepper_healthy"]["unique_image_references"], 1)
        self.assertEqual(report["target_classes"]["pepper_anthracnose"]["annotation_rows"], 1)
        self.assertEqual(report["target_classes"]["pepper_powdery_mildew"]["unique_image_references"], 1)
        self.assertEqual(report["schema_fields"]["annotation:dict"], 1)
        self.assertEqual(report["schema_fields"]["annotations:dict"], 2)

    def test_counts_duplicate_refs_multiple_classes_and_multiple_annotations(self):
        image_ref = "200_20210802_5_1_a7_1_2_13_2_0.JPG"
        self.write_label("first.json", crop=5, task=1, disease="a7", image=image_ref)
        second = {
            "description": {"image": image_ref, "date": "20210802", "width": 100,
                            "height": 80, "task": 1},
            "annotations": [
                {"crop": 5, "disease": "a7", "risk": 2, "grow": 13, "area": 1,
                 "bbox": [], "part": []},
                {"crop": 5, "disease": "a8", "risk": 2, "grow": 13, "area": 1,
                 "bbox": [], "part": []},
            ],
        }
        (self.root / "multiple.json").write_text(json.dumps(second), encoding="utf-8")

        report = analyze_labels(self.root)

        self.assertEqual(report["counts"]["duplicate_image_reference_extras"], 1)
        self.assertEqual(report["counts"]["duplicate_image_reference_names"], 1)
        self.assertEqual(report["counts"]["image_references_with_multiple_classes"], 1)
        self.assertEqual(report["counts"]["images_with_multiple_annotation_objects"], 1)
        self.assertEqual(report["target_classes"]["pepper_anthracnose"]["annotation_rows"], 2)
        self.assertEqual(report["target_classes"]["pepper_powdery_mildew"]["annotation_rows"], 1)

    def test_reports_malformed_json_schema_and_code_task_conflict(self):
        self.write_label("conflict.json", crop=5, task=0, disease="a7")
        (self.root / "broken.json").write_text("{bad", encoding="utf-8")
        (self.root / "missing.json").write_text(json.dumps({"description": {"image": "x.jpg"}}),
                                                 encoding="utf-8")

        report = analyze_labels(self.root)

        self.assertEqual(report["counts"]["json_files"], 3)
        self.assertEqual(report["counts"]["parsed_json"], 2)
        self.assertEqual(report["counts"]["json_errors"], 2)
        self.assertEqual(report["task_disease_inconsistencies"]["5|0|a7"], 1)

    def test_reports_invalid_boxes_and_filename_metadata_mismatch(self):
        self.write_label(
            "bad.json", crop=5, task=1, disease="a7",
            image="300_20210801_5_1_a7_1_2_13_2_0.JPG",
            annotation_overrides={"bbox": [{"x": 99, "y": 2, "w": 4, "h": 5}],
                                  "part": [{"x": -1, "y": 2, "w": 1, "h": 1}]},
            description_overrides={"width": 100, "height": 80},
        )

        report = analyze_labels(self.root)

        self.assertEqual(report["counts"]["filename_metadata_mismatches"], 1)
        self.assertEqual(report["counts"]["filename_metadata_mismatches"],
                         sum(report["filename_metadata_mismatches_by_field"].values()))
        self.assertEqual(report["counts"]["bbox_outside_declared_dimensions"], 1)
        self.assertEqual(report["counts"]["part_invalid"], 1)

    def test_cli_writes_new_report_but_refuses_to_overwrite(self):
        report_path = Path(self.temp.name) / "report.json"
        args = ["--label-root", str(self.root), "--output", str(report_path)]

        self.assertEqual(main(args), 1)
        self.assertEqual(json.loads(report_path.read_text(encoding="utf-8"))["counts"]["json_files"], 0)
        self.assertEqual(main(args), 2)

    def test_rejects_missing_label_directory(self):
        with self.assertRaises(ValueError):
            analyze_labels(self.root / "missing")


if __name__ == "__main__":
    unittest.main()
