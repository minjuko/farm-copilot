# 병해충 진단 모델 현황과 클래스 매핑 후속 작업

이 문서는 공개 저장소의 코드와 로컬에서 확인한 Checkpoint Metadata를 기준으로 병해충 진단 모델의 현재 상태, 확인 가능한 범위, 클래스 매핑 복원에 필요한 후속 작업을 정리합니다. 현재 작업 트리에는 모델 가중치가 추적되지 않지만, 과거 Git 이력에는 체크포인트 blob이 남아 있어 공개 접근을 차단한 상태는 아닙니다(FC07 검증 기록 참조).

## 출처와 구현 이력

- 2024년 팀 프로젝트에서 YOLO 기반 병해 진단 기능을 구현한 이력은 Git에 남아 있습니다. 당시 학습에 사용한 데이터셋은 현재 확보한 자료만으로 확정할 수 없습니다. 이전 문서는 AI Hub 153을 지목했지만, 후속 provenance 조사에서 525를 언급한 회고 기록도 확인되어 서로 충돌합니다. 학습 원본이나 변환 근거 없이 어느 쪽도 학습 출처로 단정하지 않습니다. 조사 범위는 [출처·클래스 복원 조사](../backend/evaluation/PROVENANCE.md)에 정리돼 있습니다.
- AI Hub 공개 페이지는 각 데이터셋의 이미지·라벨 구조를 설명하지만, 공개 데이터 설명만으로 이 Checkpoint가 해당 자료로 학습됐다는 뜻은 아닙니다.
- AI Hub 페이지의 공개 참고 모델과 이 프로젝트의 Checkpoint는 같은 모델이라고 볼 수 없습니다. 공개 페이지에는 질병 진단 참고 모델로 ResNet50이 기재되어 있지만, 로컬 Checkpoint는 YOLOv8l Detection Model입니다.
- 2026년 개인 개선 범위는 기존 추론 계약의 검증, 명시적 클래스 매핑, 오류 처리와 회귀 테스트 보강입니다. 원 모델 학습이나 성능 개선을 개인 작업으로 주장하지 않습니다.

## 현재 확인된 모델 계약

공개 저장소의 Runtime Code, `model_manifest.json`, 로컬 Checkpoint Metadata에서 다음 항목을 확인했습니다.

| 항목 | 확인된 값 |
| --- | --- |
| Task / Architecture | Object Detection / YOLOv8l |
| 입력 크기 | 640 |
| 출력 Class 수 | 6 |
| 원시 Confidence | `0~1` |
| 백엔드 탐지 기준 | `0.60` 이상 |
| 결과 선택 | 기준을 통과한 Box 중 최고 Confidence |
| API·DB Confidence | 원시 값을 `100`배 한 `0~100` |

현재 Checkpoint와 Backend Fixture가 요구하는 Class Metadata는 다음과 같습니다.

| class_id | Model Label | Fixture `Pest.code` | DB 표시명 |
| ---: | --- | --- | --- |
| 0 | 고추 탄저병 | `PEPPER_ANTHRACNOSE` | 고추 탄저병 |
| 1 | 고추 흰가루병 | `PEPPER_POWDERY_MILDEW` | 고추 흰가루병 |
| 2 | 오이 노균병 | `CUCUMBER_DOWNY_MILDEW` | 오이 노균병 |
| 3 | 토마토 흰가루병 | `TOMATO_POWDERY_MILDEW` | 토마토 흰가루병 |
| 4 | 오이 노균병 | `CUCUMBER_DOWNY_MILDEW` | 오이 노균병 |
| 5 | 오이 흰가루병 | `CUCUMBER_POWDERY_MILDEW` | 오이 흰가루병 |

ID 2와 4가 같은 표시명·Pest Code인 이유는 현재 저장소와 Checkpoint Metadata만으로 확정할 수 없습니다. Checkpoint가 두 출력을 별도 ID로 내므로 서비스는 둘을 각각 유지하고 현재 Fixture는 같은 `CUCUMBER_DOWNY_MILDEW` Pest에 연결합니다. 이는 출력 ID 계약을 보존하기 위한 현상 유지이지, 학습 당시 별도 질병 클래스였다는 근거는 아닙니다. 원천 라벨을 확인하기 전에는 임의로 합치거나 번호를 변경하지 않습니다.

## Checkpoint에서 확인한 학습 Metadata

로컬에만 보관된 Checkpoint를 추론 없이 읽어 다음 Metadata를 확인했습니다.

- Ultralytics Version: `8.2.63`
- Base Config: `yolov8l.yaml`
- Data Config 경로: `/content/yolo_config.yaml`
- 계획 Epoch: `100`
- 기록된 Epoch: `61`
- Batch Size: `16`
- Patience: `7`
- Seed: `2024`
- Deterministic: `true`
- Pretrained: `true`
- AMP: `true`

Checkpoint에 저장된 마지막 학습 지표도 존재하지만, 원본 데이터 분할과 평가 설정이 없어 독립적으로 재현하거나 검증하지 못했습니다. 따라서 공개 문서에서는 해당 수치를 모델 성능 근거로 사용하지 않습니다. 기록된 Epoch 수만으로 Early Stopping 발생 여부도 단정하지 않습니다.

## 현재 검증할 수 없는 부분

다음 자료가 공개 저장소에 없어 AI Hub 원천 라벨부터 서비스 질병 정보까지의 연결을 입증할 수 없습니다.

- 학습 당시의 `/content/yolo_config.yaml`
- AI Hub JSON을 YOLO Label로 변환한 Script 또는 Notebook
- 실제 Train·Validation·Test 분할 목록
- AI Hub 작물·질병 Code와 YOLO Class ID의 대응표
- 중복된 Class ID 2와 4의 생성 근거
- 학습에 추가 데이터가 사용되었는지 여부

AI Hub 공개 페이지에 열거된 질병 예시와 Checkpoint의 다섯 개 고유 표시명도 그대로 일치하지 않습니다. 이는 사용 Subset, Label 재정의 또는 추가 데이터 가능성을 검토해야 한다는 신호이며, 공개 페이지 정보만으로 현재 Mapping을 고쳐서는 안 됩니다.

## 클래스 매핑 보완 순서

매핑은 다음 연결을 증거와 함께 복원하는 방식이 적절합니다.

```text
AI Hub 작물·질병 Code
  → 학습용 Canonical Class Code
  → YOLO Class ID
  → Django PestModelClass
  → 사용자에게 제공하는 병해 상세정보
```

우선순위는 다음과 같습니다.

1. **P0 — 원본 설정 복원:** `yolo_config.yaml`, 변환 Script, 데이터 분할, 학습 Notebook에서 Class ID 생성 근거를 찾습니다.
2. **P0 — 중복 ID 판정:** ID 2와 4의 원천 JSON Code와 표본을 비교해 의도된 별도 Class인지 오류인지 결정합니다.
3. **P1 — 자동 점검:** Checkpoint preflight는 파일 무결성·task·class names·CPU inference를 확인하고, `seed_detection_catalog`은 fixture의 여섯 ID와 다섯 Pest Code를 검증합니다. FC07은 `model_manifest.json`과 런타임 계약이 어긋나지 않는 Mock 기반 회귀 검사를 추가했습니다. 기본 CI는 체크포인트 파일을 요구하지 않습니다.
4. **P1 — 재현 정보:** Checkpoint Hash, Runtime Version, Architecture, Class 목록과 학습 인자를 별도 Manifest로 관리합니다. 가중치와 로컬 경로는 포함하지 않습니다.
5. **P2 — 실제 평가:** 승인된 데이터 취득 후 고정 평가셋으로 추론, Confusion Matrix와 Class별 지표를 다시 산출하고 `0.60` 기준을 검토합니다.

원천 근거를 복원하기 전에는 Class ID 변경, 새로운 AI Hub Code 생성, 중복 Class 병합 또는 Confidence 기준 변경을 수행하지 않습니다.

## FC07 로컬 검증 기록 (2026-10-27)

아래 결과는 현재 개발 PC의 로컬 파일과 CPU 런타임에 대한 기록입니다. 현재 tree에는 체크포인트 파일이 없고, 과거 Git 이력에 남은 blob은 아래에 별도로 기록합니다.

| 항목 | 확인 결과 |
| --- | --- |
| 파일 위치 / 배포 | 로컬 `backend/best.pt`; Git에서 추적되지 않고 `*.pt` 규칙으로 무시됨 |
| 크기 / SHA-256 | 87,631,411 bytes / `b4e90d9feef9c9e35923c4e5fbf386d6e37ae6b2a3df687edfb14173bd7c10f4` |
| Checkpoint / Task / Architecture | Ultralytics 8.2.63 metadata / `detect` / `yolov8l.yaml` |
| 실행 Runtime | Python 3.11, PyTorch 2.3.1+cpu, torchvision 0.18.1+cpu, Ultralytics 8.3.169; CUDA 미사용 |
| 학습 PyTorch 버전 | Checkpoint에 기록되지 않아 확인 불가 |
| 클래스 메타데이터 | ID 0~5, 6개 이름이 Checkpoint·Manifest·Fixture 간 일치 |
| `check_detection_model` | 정상 종료; 실제 artifact 로드 및 합성 64×64 CPU smoke inference 통과 |
| 실제 opt-in 업로드 통합 테스트 | 1개 통과; 실제 로컬 이미지 업로드, DB 저장, 본인 이력·상세·private image 조회 및 타 사용자 차단 확인 |

현재 작업 트리의 `backend/best.pt`는 `.gitignore`에 의해 무시되며 추적되지 않습니다. 다만 공개 Git 이력의 `deb17cc:best.pt`에는 87,631,411 bytes가 남아 있고, 이 blob의 SHA-256은 FC07 로컬 체크포인트와 일치합니다. 따라서 과거 commit을 통해 체크포인트를 받을 수 있으며 현재 ignore 상태는 비공개를 보장하지 않습니다.

체크포인트가 공개 Repository 이력에 포함된 사실만으로 모델 가중치의 공개·재배포 허가를 입증하지 않습니다. 학습 자료, 가중치 소유권과 제3자 라이선스·배포 조건을 확인하지 못했습니다. 공개 배포가 허용된다고 가정하지 말고, 권리 확인 전에는 새로운 배포 경로에 모델을 복사하거나 별도 다운로드 링크를 만들지 않습니다. 이미 공개된 과거 이력을 정리하려면 Repository history rewrite와 일반 fast-forward가 아닌 force update가 필요하며, fork·clone·기존 다운로드에 남은 사본까지 회수할 수 없습니다. FC10에서는 승인 경계에 따라 이력 재작성이나 공개 범위 변경을 하지 않았습니다.

단일 측정은 Intel Core i7-10510U (4코어/8스레드), CPU, Python 프로세스에서 수행했습니다. 모델 로드 0.395초, 1500×2000 입력의 첫 `augment=True` 추론 4.230초, 추론 직후 프로세스 RSS 631.8 MiB였습니다. RSS는 모델만의 메모리가 아니라 Python 프로세스 전체입니다. 이 수치는 한 장·한 PC의 실행 관찰값일 뿐 정확도, 처리량 보장 또는 다른 장비의 비교 기준이 아닙니다.

실제 통합 테스트는 Django test database와 OS 임시 업로드/비공개 이미지 경로를 사용하고 종료 시 정리합니다. 공개 CI의 기본 테스트는 계속 Mock 기반이며 이 opt-in 테스트는 모델이 없는 환경에서 skip됩니다. 이번 실행에서는 Ultralytics가 비 ASCII 라벨을 그리기 위해 `Arial.Unicode.ttf` 글꼴을 임시 디렉터리에 자동 다운로드했습니다. 해당 임시 파일은 테스트 후 제거했습니다. Checkpoint나 원본 데이터는 내려받지 않았고, 농업 API도 호출하지 않았습니다. 글꼴 다운로드는 Ultralytics plotting의 외부 asset 동작이며, 네트워크 차단 운영 환경에서 annotation이 필요한 경우 별도 글꼴 배포 경계를 정해야 합니다.

이번 검증은 한 참고 이미지에 대한 실행 가능성 확인입니다. 정확도나 일반화 성능은 검증하지 않았습니다. 원 학습 데이터, 변환 스크립트, 원본 AI Hub JSON과 YOLO ID 대응표는 확보하지 못했습니다. ID 2와 4는 각각 별도 출력 ID로 남아 있으나 같은 `CUCUMBER_DOWNY_MILDEW` Pest를 가리키는 이유는 미해결입니다.

## 공개 저장소 정책

- 새 변경에서는 `*.pt`, 원본 학습 데이터, 변환 중간 산출물과 로컬 분석 기록을 Git에 추가하지 않습니다. 현재 tree에서 `*.pt`는 ignore되지만, 과거 이력의 blob 제거는 별도 history rewrite가 필요합니다.
- 가중치 배포 허용 여부는 확인되지 않았습니다. 공개 정책 결정 전에 모델의 생성·소유권 및 원 학습 데이터 조건을 확인해야 합니다.
- 공개 저장소에는 실행 계약, 검증 가능한 Mapping, Setup 방법과 재현 한계만 문서화합니다.
- Mock 기반 테스트는 모델 미탑재 환경의 API 계약과 오류 처리를 검증하지만 실제 YOLO 성능을 검증하지 않습니다.
