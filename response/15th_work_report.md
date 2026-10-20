# 15차 작업 보고서

## 1. 요약

14차까지 누적된 AI 관련 변경을 검토하고 기능별 로컬 커밋 4개로 정리했다. backend 전체 테스트 223개, frontend 전체 테스트 183개, frontend 빌드가 통과했다. 기존 Ruff 지적 3건은 새로 발생한 오류가 아님을 14차 보고와 대조했고 자동 수정하지 않았다. 원격 저장소에는 push하지 않았다.

작업 전 HEAD는 `743d246`이었고 `origin/main`과 같았다. 현재 브랜치는 `main`이며 새 커밋 4개가 로컬에 추가됐다. 추적 중인 미커밋 변경은 없고, 아래에 기록한 비추적 파일은 사용자 작업/운영 기록 등의 성격을 고려해 남겨 두었다.

## 2. 변경 파일 분류

| 기능 | 커밋 | 포함 파일 |
|---|---|---|
| AI Hub 데이터 준비 | `3fe1a6e` | `backend/data_preparation/`의 구현, 테스트, README/AUDIT 19개와 루트 `.gitignore` 1개. ZIP/이미지 추출, label 분석, manifest 생성, subset 준비 및 resize 관련 기능이다. |
| MobileNet 분류 모델 파이프라인 | `9d743d6` | `backend/model_training/` 12개. dataset/split, class 설정, 학습·평가·하드웨어 점검, 테스트, 선택적 Colab notebook을 포함한다. |
| 읽기 전용 분류 평가 | `c9da340` | `backend/evaluation/` 11개. 별도 평가 dataset 설계, provenance, 설정 예시, 평가 스크립트와 테스트를 포함한다. |
| YOLO 진단 readiness 및 운영 | `284c0ef` | detection artifact 계약/manifest/preflight, 안전한 Pest 카탈로그 seed, capabilities readiness, 테스트 및 `docs/AI_DETECTION_OPERATIONS.md` 등 11개. |

첫 커밋의 `.gitignore`에는 작업 전부터 존재한 `New_Sample/` 보호 규칙이 포함됐다. 로컬 데이터 보호 목적이 명확해 데이터 준비 기능과 함께 커밋했으며, 그 외 미확인 사용자 변경은 stage하지 않았다.

## 3. 커밋 내역

| 순서 | Commit | 메시지 | 범위 및 확인 |
|---:|---|---|---|
| 1 | `3fe1a6e` | `feat(data): add AI Hub dataset preparation pipeline` | 20 files. 데이터 준비 코드와 테스트. 전체 backend 테스트에서 관련 테스트 포함 통과. |
| 2 | `9d743d6` | `feat(ml): add configurable image classification pipeline` | 12 files. 분류 학습 파이프라인. 전체 backend 테스트에서 관련 테스트 포함 통과. Notebook 4개 cell, 저장 출력 0개로 확인했다. |
| 3 | `c9da340` | `feat(ml): add read-only classification evaluation workflow` | 11 files. 평가 도구, 예시 설정, provenance 문서와 테스트. 전체 backend 테스트에서 관련 테스트 포함 통과. |
| 4 | `284c0ef` | `feat(detect): validate model artifacts and catalog readiness` | 11 files. 모델 무결성 및 CPU preflight, 카탈로그 seed 및 readiness 검사. 전체 backend 테스트와 실제 로컬 artifact preflight 통과. |

## 4. 검증 결과

- Backend: Django 전체 테스트 **223개 통과**, system check 오류 없음.
- Frontend: **32 suites, 183 tests 통과**.
- Frontend build: 성공.
- 실제 detection preflight: 승인 모델 SHA-256/크기, 클래스 계약, CPU smoke inference 통과. Ultralytics cache 쓰기 경고는 있었지만 검사 결과에는 영향이 없었다.
- Ruff 전체 검사: 기존 지적 3건 외 신규 오류 없음. `backend/data_preparation/analyze_label_archive.py`의 I001, `inspect_dataset.py`의 F841, `tests/test_inspect_dataset.py`의 F401이며 14차 보고서에서 확인한 항목이다. 자동 수정하지 않았다.
- `git diff --check`, staged diff 검사 통과.
- `backend/best.pt`, `backend/model_training/checkpoint.pth`, 데이터 준비 디렉터리의 원본 ZIP이 각각 `*.pt`, `*.pth`, `data/` ignore 규칙에 걸리는 것을 확인했다.

## 5. 보안 및 파일 제외

커밋 대상 파일에서 실제 API key 값, access token, 실제 비밀번호 또는 `.env` 내용이 포함되지 않았음을 검토했다. 평가 문서에 있는 예시 credential은 테스트용 문자열이다. 노트북은 저장된 셀 출력이나 API key가 없고, 학습 실행은 기본 비활성 설정이다.

모델 파일은 87,631,411 bytes, SHA-256 `b4e90d9feef9c9e35923c4e5fbf386d6e37ae6b2a3df687edfb14173bd7c10f4`로 manifest에만 기록했다. 모델 checkpoint, AI Hub 원본 ZIP 및 파생 데이터/실험 산출물은 Git에 넣지 않았다.

다음 비추적 자료는 목적 및 민감한 로컬 경로/환경 정보/개인 작업 맥락을 고려해 제외했고 삭제하지 않았다.

- `request/10th_request.md`부터 `request/15th_request.md`까지의 작업 프롬프트.
- `response/10th_work_report.md`부터 `response/14th_work_report.md`까지의 이전 보고서.
- `docs/AI_HUB_525_*_2026-10-20.txt` 운영·감사 로그 9개.
- `docs/AI_HUB_525_COLAB_PREPARATION_2026-10-20.md`, `docs/AI_HUB_525_LOCAL_GPU_AND_DATA_OPTIMIZATION_2026-10-20.md`의 로컬 운영 스냅샷.
- 저장소 루트의 한글 이름 PDF 2개. 출처와 프로젝트 산출물로서의 포함 목적이 확인되지 않아 보류했다.
- `.env`, 로컬 DB/캐시, 원본 데이터, 모델·체크포인트 등 ignore 대상 산출물.

이 파일 목록은 작업 마감 시점의 상태 기준이다. 비추적 자료는 사용자 원본으로 남겨 두었고 이번 커밋에 포함되지 않았다.

## 6. 남은 작업

- Ruff 기존 지적 3건은 범위 확인 후 별도 정리할 수 있다.
- 독립적인 검증 dataset으로 분류 모델을 평가하고, 실제 배포 환경에서 artifact 보관 및 readiness 절차를 확인할 수 있다.
- 제외한 PDF와 운영 스냅샷은 소유/목적 확인 후 필요하면 별도의 문서 정리 작업으로 다룬다.

현재 작업은 로컬 커밋까지 완료됐다. 원격 push, 강제 reset/clean, 불특정 전체 stage는 수행하지 않았다.
