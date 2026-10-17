# 병해충 진단 모델 현황과 클래스 매핑 후속 작업

이 문서는 공개 저장소의 코드와 로컬에서 확인한 Checkpoint Metadata를 기준으로 병해충 진단 모델의 현재 상태, 확인 가능한 범위, 클래스 매핑 복원에 필요한 후속 작업을 정리합니다. 학습 데이터와 모델 가중치는 공개 저장소에 포함하지 않습니다.

## 출처와 구현 이력

- 2024년 팀 프로젝트에서 AI Hub [「시설 작물 질병 진단 이미지」](https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=data&currMenu=11&dataSetSn=153&topMenu)를 활용해 YOLO 기반 병해 진단 기능을 구현했습니다.
- AI Hub 공개 페이지는 JPEG 이미지와 JSON 라벨, 작물·질병·위험도 및 Bounding Box 정보를 제공한다고 설명합니다.
- AI Hub 페이지의 공개 참고 모델과 이 프로젝트의 Checkpoint는 같은 모델이라고 볼 수 없습니다. 공개 페이지에는 질병 진단 참고 모델로 ResNet50이 기재되어 있지만, 로컬 Checkpoint는 YOLOv8l Detection Model입니다.
- 2026년 개인 개선 범위는 기존 추론 계약의 검증, 명시적 클래스 매핑, 오류 처리와 회귀 테스트 보강입니다. 원 모델 학습이나 성능 개선을 개인 작업으로 주장하지 않습니다.

## 현재 확인된 모델 계약

공개 저장소의 Runtime Code와 로컬 Checkpoint Metadata에서 다음 항목을 확인했습니다.

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

| class_id | Model Label | Backend Mapping |
| ---: | --- | --- |
| 0 | 고추 탄저병 | 고추 탄저병 |
| 1 | 고추 흰가루병 | 고추 흰가루병 |
| 2 | 오이 노균병 | 오이 노균병 |
| 3 | 토마토 흰가루병 | 토마토 흰가루병 |
| 4 | 오이 노균병 | 오이 노균병 |
| 5 | 오이 흰가루병 | 오이 흰가루병 |

ID 2와 4가 같은 표시명인 이유는 현재 저장소와 Checkpoint Metadata만으로 확정할 수 없습니다. 서로 다른 원천 라벨을 같은 질병명으로 합친 것인지, 데이터 변환 또는 학습 설정의 중복인지 확인하기 전에는 임의로 합치거나 번호를 변경하지 않습니다.

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
3. **P1 — 자동 점검:** Checkpoint 이름 목록, Fixture, DB Mapping이 정확히 일치하는지 확인하는 관리 명령 또는 CI 검사를 추가합니다. Checkpoint가 없는 기본 CI는 계속 통과해야 합니다.
4. **P1 — 재현 정보:** Checkpoint Hash, Runtime Version, Architecture, Class 목록과 학습 인자를 별도 Manifest로 관리합니다. 가중치와 로컬 경로는 포함하지 않습니다.
5. **P2 — 실제 평가:** 승인된 데이터 취득 후 고정 평가셋으로 추론, Confusion Matrix와 Class별 지표를 다시 산출하고 `0.60` 기준을 검토합니다.

원천 근거를 복원하기 전에는 Class ID 변경, 새로운 AI Hub Code 생성, 중복 Class 병합 또는 Confidence 기준 변경을 수행하지 않습니다.

## 공개 저장소 정책

- `*.pt`, 원본 학습 데이터, 변환 중간 산출물과 로컬 분석 기록은 Git에서 제외합니다.
- 공개 저장소에는 실행 계약, 검증 가능한 Mapping, Setup 방법과 재현 한계만 문서화합니다.
- Mock 기반 테스트는 모델 미탑재 환경의 API 계약과 오류 처리를 검증하지만 실제 YOLO 성능을 검증하지 않습니다.
