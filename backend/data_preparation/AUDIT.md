# AI Hub 525 sample audit and training preparation

Audit date: 2026-10-20. This is a local sample inspection, not a full-corpus
audit or a model result. The original `backend/best.pt`, service code, database,
and frontend were not changed. No training or dataset download was performed.

## Evidence and scope

The repository's `New_Sample/` contains two branches: labeling JSON and source
images. It contains 110 `.json` files and 110 `.jpg` files. Every JSON
`description.image` points to exactly one image; all 110 labels parse; all 110
images open; no duplicate image references, missing pairs, or boxes outside
the declared image dimensions were found. Pillow identifies each image as
MPO, at 5152x3864 pixels. This file-format result should be checked against
the downloaded full corpus before selecting a decoder or conversion path.

The files use a JSON root with `description` and plural `annotations` objects.
The observed fields are:

| Section / field | Observed shape | Notes |
|---|---|---|
| `description.image` | string | Image filename; matched case-insensitively |
| `description.width`, `height` | integer | 5152 x 3864 for all sample rows |
| `description.date`, `time`, `region`, `task` | string/integer | Metadata; no plant/group identifier established |
| `annotations.crop` | integer | `5` in all 110 rows; code meaning not independently decoded here |
| `annotations.disease` | string | `a7` in all 110 rows; disease-name mapping is unverified |
| `annotations.risk` | integer | `2`: 54 rows; `3`: 56 rows |
| `annotations.area`, `grow` | integer | `area=1`, `grow=13` in all rows |
| `annotations.bbox` | list of `{x,y,w,h}` | Exactly one per row; documented as the object of interest |
| `annotations.part` | list of `{x,y,w,h,id}` | 1: 58, 2: 39, 3: 9, 4: 4 rows; documented as disease-part boxes |

Observed values above are measurements of the supplied lightweight sample.
They are not class definitions for the complete approved dataset. In
particular, the sample folder label indicates pepper disease data, but the
authoritative meaning of code `a7` and crop code `5` must be checked against
the matching AI Hub data guide/codebook. Folder names and filename fragments
are not accepted as a substitute for that codebook.

The official [AI Hub 525 page](https://aihub.or.kr/aihubdata/data/view.do?aihubDataSe=realm&currMenu=&dataSetSn=525&topMenu=)
describes 2021 JPG/JSON data with a dataset size of 684,616, multiple crop
states, and official model work using ResNet50 classification. Its published
schema calls the singular object `annotation`; this supplied sample instead
uses `annotations`. The page defines `bbox` as the focus-object box and
optional `part` as disease-part boxes. The sample scanner accepts either
annotation key spelling but does not transform either box type. The public
page lists disease codes (`00`, `a1`-`a12`, `b1`-`b8`, `c1`-`c7`, `c9`, `c11`,
`c12`) and crop codes `1`-`6`; the accessible schema table does not map each
code to the five target disease names. Official class-name mapping therefore
remains pending the downloaded guide/codebook.

AI Hub's public composition table reports 13,547 pepper anthracnose, 12,198
pepper powdery mildew, 11,690 cucumber downy mildew, 16,675 cucumber powdery
mildew, and 14,704 tomato powdery mildew images. It lists 55,150 pepper,
51,252 cucumber, and 54,093 tomato normal images. These are provider-published
dataset statistics, not counts verified in the local sample or proof that the
entire category is included in the user's approved download. Other disease,
physiological-disorder, and pesticide-response categories must be filtered
only after confirming the codebook and subset contents.

## Target mapping status

| New class | Required source evidence | Status in this sample |
|---|---|---|
| Pepper anthracnose | crop and disease codes in official codebook | Not verified (`5/a7` observed, mapping unverified) |
| Pepper powdery mildew | codebook | Not present / not verifiable |
| Cucumber downy mildew | codebook | Not present / not verifiable |
| Cucumber powdery mildew | codebook | Not present / not verifiable |
| Tomato powdery mildew | codebook | Not present / not verifiable |
| Healthy / normal | explicit normal source label and crop code | Not present |

No ID mapping was generated. Do not map `a7` to a disease based only on its
value, folder path, or existing model names. Do not carry over the old YOLO
class IDs, including the unresolved duplicate IDs 2 and 4.

## Model task recommendation

Start with an **image-classification baseline** for the five target diseases
plus an explicit normal class, subject to the codebook and full-data audit.
The user-facing task is a whole-image diagnosis; the dataset supplies
image-level crop/state labels and its official public model example is
classification. A disease detector would need to use `part` boxes only after
review confirms that their semantics and coverage are consistent across all
selected disease classes. `bbox` encloses the focus object and should not be
treated as a lesion box. Keep localization as a follow-on experiment if users
need visual evidence. For either task, unsupported crop/disease and low
confidence handling require separately labelled validation examples and a
service-level abstention policy; this work does not modify the service.

This is a preliminary task recommendation, not permission to train. Full
classes, normal data, data split, license terms, group metadata, and label
coverage still need review before conversion or training.

## Data design before conversion

1. Keep AI Hub files immutable and outside Git. `New_Sample/` is Git-ignored.
   Derived data should live under a separate local output directory and have
   a source/version/license register.
2. Obtain the official data guide and category/code table from the approved
   download, then verify each intended `(crop, disease)` pair against source
   JSON plus sampled images. Maintain a new, versioned class map independent
   of the legacy checkpoint.
3. Audit the full corpus: per-class counts, normal/unsupported categories,
   image/label pairings, unreadable files, box bounds, optional `part` coverage,
   duplicate hashes, and source/augmentation relationships. The sample is
   explicitly lightweight and may differ from originals.
4. Do not split at file-random level. Find documented plant/capture/origin
   grouping fields in the full guide or download. Group source and augmented
   versions together. Reserve one fixed test split; tune thresholds using
   validation only. If no grouping key exists, report the leakage risk and
   do not call the split fully independent.
5. Record dataset ID/version, exact acquired archives, license/use scope,
   transformation version, source file hashes, class map revision, split
   manifest hash, and environment. Do not commit source data or local reports.

## Environment choice

| Environment | Role | Assessment |
|---|---|---|
| CPU | Schema audit, conversion, unit tests, small inference checks | Available through the existing backend virtual environment; not proposed for full training |
| GTX 1650 4 GB | Small pilot only | VRAM is tight for 5152x3864 source images; resize/crop and batch-size experiments would be needed. No GPU runtime was verified during this audit |
| Google Colab GPU | First training candidate after data audit | More practical for a training pilot; runtime GPU type and availability vary and must be recorded per run |
| Other GPU | Alternative only if user confirms access | No other GPU environment was verified |

YOLOv8n is the first detector candidate only if the audited task is detection;
YOLOv8s can be a second controlled comparison. For the recommended
classification baseline, compare an appropriately small classifier and record
the Ultralytics/PyTorch versions. Do not choose input size, batch size, epochs,
or model family until full data sizes and an actual training GPU are known.

## Tool and test

`inspect_dataset.py` is a read-only aggregate scanner. It reports file pairing,
image decode/dimensions, observed schema and source-code counts, per-image box
counts, invalid coordinates, and boxes beyond declared dimensions. It never
creates class names or labels. Its tests use temporary synthetic images and
annotations; no sample data is copied into test fixtures.

Run from repository root:

```powershell
backend/.venv/Scripts/python.exe backend/data_preparation/inspect_dataset.py --data-root New_Sample
backend/.venv/Scripts/python.exe -m unittest discover -s backend/data_preparation/tests -t backend -v
```

At this audit, the command completed with 110/110 pairs, zero corrupt images,
zero malformed JSON, zero out-of-bounds boxes, and zero image/label dimension
mismatches. The five isolated tests passed.
No model evaluation or training was performed.

## Next inputs needed

- Full approved 525 archive (or AI Hub Shell accessible root) containing all
  selected diseases and normal cases. Download only when the user explicitly
  asks to proceed.
- The matching data guide, crop/disease code tables, any split/group or
  augmentation documentation, and dataset version/archive list.
- License/use restrictions relevant to local training, derived data, and
  portfolio screenshots or public release.
- Confirmed GPU runtime access (Colab GPU is the initial candidate).

Once supplied, run the scanner over the full source, review source-code
distributions and image samples, then author a versioned code map and
conversion tests. Only after those checks should a separate approval-gated
training task produce a new checkpoint alongside `best.pt`.
