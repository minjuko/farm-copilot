# AI Hub 525 data preparation

This package starts with **read-only inspection**. It does not rename source
classes, convert labels, split data, resize images, or train a model. Those
steps stay gated until the downloaded dataset's codebook, license terms, and
grouping metadata have been reviewed.

## Inspect a local dataset

From the repository root:

```powershell
backend/.venv/Scripts/python.exe backend/data_preparation/inspect_dataset.py `
  --data-root New_Sample
```

Write an aggregate JSON report outside the source-data tree:

```powershell
backend/.venv/Scripts/python.exe backend/data_preparation/inspect_dataset.py `
  --data-root "<dataset-root>" `
  --output "<workspace>/backend/data_preparation/local/525-inspection.json"
```

When images and labels are stored separately, pass both roots directly; this
avoids copying a large image corpus into a combined directory:

```powershell
backend/.venv/Scripts/python.exe backend/data_preparation/inspect_dataset.py `
  --image-root "<image-root>" `
  --label-root "<label-root>" `
  --output "<report-path>/pepper-image-label-inspection.json"
```

For a quick pairing/integrity pass that skips image SHA-256 hashing, add
`--skip-hashes`. The default performs full-file hashes for duplicate-byte
detection.

The report contains counts and source codes, not disease-name guesses. Exit
status is `0` when the scan completes without malformed labels, unreadable
images, hash errors, size mismatches, or out-of-bounds boxes; `1` when any are
found; and `2` when the input root cannot be read. The source tree is never
written. The local report directory is Git-ignored. The scanner walks files
incrementally, keeps filename and hash indexes in temporary SQLite storage,
and caps stored error details at 100. It prints progress every 10,000 files.
Use `--progress-every 0` to disable progress or `--skip-hashes` for a faster
first pass without full-file SHA-256 duplicate checking.

## Current sample boundary

The repository's `New_Sample/` is excluded from Git. It is a lightweight
AI Hub sample, not the complete training corpus; sample files may be modified
or masked by the provider. The official guide verifies the five target disease
codes, but the sample does not establish full-corpus class balance or
train/validation/test coverage.

The official 525 schema distinguishes `annotations.bbox` (the annotated
object of interest) from optional `annotations.part` (disease-part boxes).
These annotations must not be merged. Confirm which box is appropriate for
the product objective before choosing detection targets. Images with a
verified normal condition can be used as classification negatives; detection
needs a documented empty-label convention for such images.

## Analyze labels before images are downloaded

The pepper label archive can be analyzed independently of the image archive:

```powershell
backend/.venv/Scripts/python.exe backend/data_preparation/analyze_label_archive.py `
  --label-root "<label-root>" `
  --output "<report-path>/tl1-pepper-analysis.json"
```

The label-only analyzer reports schema variants (`annotation` and
`annotations`), source-code combinations, the three verified pepper classes,
image-reference duplicates, filename/JSON metadata consistency, date/time/
region coverage, box statistics, and parse errors. It never checks image
existence, decoding, image hashes, or visual duplication. It caps detailed
error paths, writes only aggregate fields plus bounded errors, and refuses to
overwrite an existing output report. An empty label directory returns a
nonzero status so it cannot be mistaken for a completed analysis.

The observed AI Hub pepper filename format abbreviates the healthy disease
code `00` to `0`; the analyzer normalizes this one documented-by-data
representation when comparing filename and JSON codes.

Verified first-experiment codes are pepper healthy `(crop=5, task=0,
disease=00)`, pepper anthracnose `(5, 1, a7)`, and pepper powdery mildew
`(5, 1, a8)`. These code combinations still need to be checked against every
record in the downloaded labels.

## Tests

```powershell
backend/.venv/Scripts/python.exe -m unittest discover `
  -s backend/data_preparation/tests -t backend -v
```

The tests synthesize tiny images and labels under temporary directories. The
label-only tests intentionally omit image files to verify that this is a valid
analysis mode.

## Inspect a sample from an image archive without extraction

When labels are in WSL and the archive is on a Windows drive, export only selected class metadata to a Git-ignored local directory. The CSV contains original image references and must not be committed:

```bash
python3 backend/data_preparation/export_label_manifest.py \
  --label-root "<path-to-TL1-pepper-labels>" \
  --output "<workspace>/backend/data_preparation/data/aihub525/derived/manifests/ts1_a7_manifest.csv" \
  --crop 5 --task 1 --disease a7
```

Inspect a deterministic risk-balanced sample directly from the ZIP with Pillow; image files are streamed and never extracted:

```powershell
backend/.venv/Scripts/python.exe backend/data_preparation/inspect_archive_sample.py `
  --archive backend/data_preparation/data/aihub525/raw/archives/51651/104.식물_병_유발_통합_데이터/01.데이터/1.Training/원천데이터/TS1_고추_병해1.zip `
  --label-manifest backend/data_preparation/data/aihub525/derived/manifests/ts1_a7_manifest.csv `
  --crop 5 --task 1 --disease a7 --sample-size 200 --seed 2026 `
  --output backend/data_preparation/data/aihub525/reports/ts1_a7_sample.json
```

The report contains original filenames and image hashes, so keep it in the ignored local data tree. Its quality and duplicate findings apply only to the selected sample; dHash matches are candidates for manual review. Pillow may report JPEG-based MPO images as `MPO`, which is compatible with `.jpg`.
