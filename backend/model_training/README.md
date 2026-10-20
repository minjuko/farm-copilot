# Farm Copilot pepper classifier (Colab-ready)

This package is independent from Django/React and the existing `backend/best.pt`.
Its default class map preserves the original three-class experiment. The
separate `aihub_2class_config.json` defines the AI Hub 525 2-class experiment:

| ID | Class | crop/task/disease |
|---:|---|---|
| 0 | pepper_healthy | 5 / 0 / 00 |
| 1 | pepper_anthracnose | 5 / 1 / a7 |
| 2 | pepper_powdery_mildew | 5 / 1 / a8 |

The source dataset, a 40-image anthracnose-only technical subset, and training
splits are separate. The subset manifest deliberately says `split=unassigned`
and has no plant `group_id`; it must not be used as a classifier benchmark.
Training stops unless every split has all configured classes, image
hashes match, labels match this contract, and group IDs are present and do not
cross splits.

## Local technical subset

From the repository root, using the existing 200-image audited report:

```powershell
backend/.venv/Scripts/python.exe backend/data_preparation/prepare_classification_subset.py `
  --archive backend/data_preparation/data/aihub525/raw/archives/51651/104.식물_병_유발_통합_데이터/01.데이터/1.Training/원천데이터/TS1_고추_병해1.zip `
  --sample-report backend/data_preparation/data/aihub525/reports/ts1_a7_sample_200_seed2026_final.json `
  --output-dir backend/data_preparation/data/aihub525/derived/subsets/pepper_a7_tech_40_v1 `
  --sample-size 40 --seed 2026
```

The command verifies each selected source hash against the audit report, reads
only selected ZIP members, applies EXIF orientation, converts to RGB JPEG, and
writes a local manifest with source/derived hashes. It does not alter the ZIP.
Its output is Git-ignored. The source group is unknown, so the rows remain
unassigned and cannot be split or trained.

## Colab setup and training

1. Confirm the AI Hub 525 terms and your account's authorization permit storing
   the selected derived images in Google Drive/Colab. This audit has not
   uploaded any source or derived images.
2. In Drive, create `farm-copilot-ai/code/` and place this repository's
   `backend/model_training/` package there. Put the approved prepared dataset
   at `farm-copilot-ai/datasets/pepper-v1/`, with its `manifest.csv` and image
   paths preserved under the dataset root. Keep original archives outside the
   Colab working directory unless terms and capacity explicitly permit them.
3. Open `colab_train.ipynb` in Colab. Check the runtime preflight cell. GPU
   availability is dynamic and is not guaranteed; the free runtime can end and
   its local filesystem is ephemeral. Use Drive only for files that need to
   persist.
4. Set `RUN_TRAINING = True` only after the manifest has group-based train/val/
   test assignments and passes the strict validation. Change the dataset and
   output paths in the notebook if your Drive folder differs.

The notebook does not install packages, download AI Hub data, upload local
files, or start a paid resource. It reports Python/PyTorch/torchvision/GPU and
Drive/local free space, copies the prepared dataset from Drive to Colab's
`/content` disk for training, then invokes this script. Experiment outputs are
written to Drive. The model is torchvision MobileNetV3-Small
with ImageNet weights by default. The first training run may download those
weights; `--no-pretrained` disables that network access but is not the intended
baseline. Record the versions actually shown by the Colab runtime.

## Group split and training CLI

After independently establishing group IDs (same-plant/sequence and exact
duplicates must stay together), run the deterministic allocator:

```bash
cd /content/drive/MyDrive/farm-copilot-ai/code
python -m model_training.split_manifest --input /content/drive/MyDrive/farm-copilot-ai/datasets/pepper-v1/manifest_unassigned.csv \
  --output /content/drive/MyDrive/farm-copilot-ai/datasets/pepper-v1/manifest.csv \
  --class-config model_training/aihub_2class_config.json \
  --seed 2026 --train-ratio 0.70 --val-ratio 0.15 --test-ratio 0.15
```

It requires at least three distinct groups in each class-pattern bucket and
fails if any final split lacks a class. Review the generated counts and groups
before training. It does not infer plant identity from date/time or filename.

Equivalent direct run:

```bash
cd /content/drive/MyDrive/farm-copilot-ai/code
python -m model_training.train_classifier --manifest /content/drive/MyDrive/farm-copilot-ai/datasets/pepper-v1/manifest.csv \
  --data-root /content/drive/MyDrive/farm-copilot-ai/datasets/pepper-v1 \
  --output-dir /content/drive/MyDrive/farm-copilot-ai/experiments/baseline/run-001 \
  --class-config model_training/aihub_2class_config.json \
  --epochs 5 --batch-size 16 --image-size 224 --seed 2026 --device auto
```

## AI Hub two-class subset preparation (after TS5 is obtained)

Do not extract the TS5 archive wholesale. First export separate local CSV files
from TL1 for the two codes (`crop=5/task=0/disease=00` and
`crop=5/task=1/disease=a7`) using `data_preparation/export_label_manifest.py`.
Then run `data_preparation/prepare_aihub_classification_subset.py` with the
TS5 ZIP for healthy and the preserved TS1 ZIP for anthracnose, plus both CSVs.
It scans each ZIP's member names, requires enough exact label
matches in the archive, deterministically samples 100 per class by default,
reads only selected members, writes EXIF-corrected RGB JPEGs (long side at most
768, quality 90), and records source/derived SHA-256 values. Output rows remain
`unassigned` with blank group IDs; establish verified groups before splitting.
The output directory must not already exist and should be Git-ignored.

Example command shape (use the real local paths after TS5 is available):

```powershell
backend/.venv/Scripts/python.exe backend/data_preparation/prepare_aihub_classification_subset.py `
  --class-config backend/model_training/aihub_2class_config.json `
  --class-input "pepper_healthy=<TS5 ZIP>=<healthy TL1 manifest>" `
  --class-input "pepper_anthracnose=<TS1 ZIP>=<anthracnose TL1 manifest>" `
  --output-dir "<new local output directory>" --sample-size 100 --seed 2026
```

The output directory must not exist. Outputs include the best validation
checkpoint, epoch history, and a run record with manifest SHA-256, class map,
hyperparameters, versions, test metrics, and inference latency. The selected
checkpoint is restored from best validation Macro F1 before the test set is
evaluated once. Metrics are classwise Precision/Recall/F1, Macro F1, confusion
matrix, accuracy, and healthy-image disease false-positive rate. It also saves
test predictions and a test-only error list with relative image paths for local
review; keep these outputs private with the dataset. Test metrics must not be
used to choose settings. This is a baseline, not a clinical or agronomic
diagnosis guarantee.

## Local hardware and storage benchmarks

The hardware benchmark measures MobileNetV3-Small forward/backward/optimizer
steps with random initialization, so it does not download ImageNet weights or
produce model quality metrics. It reports CPU/CUDA device information,
throughput, peak allocated CUDA memory, and an estimated 40-image epoch time.
The estimate is compute-only and excludes data loading and validation:

```powershell
cd backend
.venv/Scripts/python.exe -m model_training.benchmark_hardware `
  --device auto --batches 4 8 16 --image-size 224 `
  --warmup 1 --iterations 3 --output data/aihub525/reports/mobilenet_benchmark.json
```

Use `backend/data_preparation/resize_classification_subset.py` to create
512/768/1024-pixel-longest-side JPEG variants under a new local derived path.
The tool refuses to overwrite an existing output directory and records per-file
source/derived hashes and aggregate byte savings. It does not assess classifier
accuracy or guarantee retention of tiny disease details.

For future experiments, assign group IDs from verified evidence, record
uncertain grouping as a limitation, inspect dHash candidates, and keep the
test split fixed. The one-class subset produced in this stage cannot satisfy
the trainer's three-class contract.
