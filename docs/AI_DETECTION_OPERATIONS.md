# AI 병해충 진단 운영 절차

## 모델 파일 준비

`best.pt`는 용량이 크고 별도 관리가 필요해 Git에 포함되지 않는다 (`*.pt` ignore). 승인된 체크포인트를 `backend/best.pt`에 배치하거나 `YOLO_MODEL_PATH`에 절대 경로 또는 `backend/` 기준 상대 경로를 설정한다. 모델 계약과 고정 SHA-256은 `backend/detect/model_manifest.json`에 기록돼 있다.

현재 승인 artifact는 87,631,411 bytes, SHA-256 `b4e90d9feef9c9e35923c4e5fbf386d6e37ae6b2a3df687edfb14173bd7c10f4`다. 검증 오류가 나면 신뢰된 원본 보관소에서 같은 버전의 파일을 다시 받아 배치하고 사전검사를 재실행한다. 애플리케이션은 자동 다운로드나 대체를 하지 않는다.

AI 런타임은 `backend/requirements-ai.txt`의 OpenCV, PyTorch, torchvision, Ultralytics 항목을 설치한다. 사전검사:

```powershell
cd backend
python manage.py check_detection_model
```

다른 위치의 artifact를 검사하려면 `--model-path <path>`를 지정한다. 명령은 존재·크기·SHA-256, 런타임 import, YOLO 로딩, `detect` task, 6개 클래스 ID/이름, 합성 64x64 이미지의 CPU smoke inference를 검사한다. 종료 코드는 성공 시 0, 실패 시 non-zero이며 파일 누락·무결성·런타임·로딩·계약·추론 실패를 사람이 읽을 수 있게 구분한다. Smoke test는 모델 실행 가능성만 검사하고 정확도나 실제 작물 분류 성능을 평가하지 않는다.

## 질병 카탈로그 초기화

새 환경에서 필요한 다섯 `Pest` 설명과 여섯 `PestModelClass` 연결만 초기화한다.

```powershell
cd backend
python manage.py seed_detection_catalog
```

입력 원본은 기존 `detect/fixtures/model_classes.json`이다. 명령은 기존 사용자, 진단 기록, 게시글 및 다른 질병 행을 삭제하지 않으며 PK를 강제로 지정하지 않는다. 같은 내용은 반복 실행 시 건너뛴다. 같은 자연 키의 상세 내용 또는 class ID의 매핑이 fixture와 다르면 트랜잭션 전체를 실패시켜 조용한 덮어쓰기를 막는다. 먼저 분리된 테스트 DB에서 실행과 검증을 마친 뒤에만 승인된 배포 절차로 적용한다. 개발/운영 DB에는 이 작업에서 명령을 실행하지 않았다.

Class ID 0..5는 모두 유지한다. ID 2와 4는 서로 다른 모델 출력 ID를 보존하면서 동일한 `CUCUMBER_DOWNY_MILDEW` Pest로 연결된다.

## Capabilities와 Readiness

`GET /api/capabilities/`의 `detection` 응답은 기존 필드를 유지한다.

```json
{"status":"available","available":true,"reason":null}
```

`available`은 artifact 무결성, PyTorch/Ultralytics import, 체크포인트 로딩과 클래스 계약, CPU smoke inference, 여섯 DB 매핑 및 상세 진단 필드가 준비된 경우에만 true다. 미준비 시 `status`는 `limited`, `available`은 false이며 `reason`은 `model_missing`, `model_integrity_mismatch`, `runtime_unavailable`, `model_load_failed`, `model_contract_mismatch`, `inference_unavailable`, `catalog_incomplete`, `database_unavailable` 중 하나다. 내부 절대 경로와 예외 스택은 API 응답에 포함하지 않는다.

모델 해시·로드·smoke 검사는 프로세스에서 파일의 절대 경로, 크기, 수정 시각 조합별 한 번 실행하고 그 결과를 메모리에 캐시한다. 다른 fingerprint가 관찰되면 다음 검사에서 다시 확인한다. 카탈로그는 매 capabilities 조회마다 읽으므로 seed 또는 DB 복구가 다음 요청에 반영된다. 같은 크기와 수정 시각을 유지한 채 파일 내용을 교체하는 특수한 경우는 실행 중 자동 탐지하지 못할 수 있으므로 artifact 교체 후에는 앱 프로세스를 재시작하고 preflight를 수행한다.

장애 확인 순서: `YOLO_MODEL_PATH`와 파일 배치 확인 → `check_detection_model` 실행 → `seed_detection_catalog`은 먼저 분리된 DB에서 충돌 여부 확인 → DB 연결 및 상세 행 확인 → 서비스 프로세스 재시작 후 capabilities 재조회. CI와 운영 DB에는 자동 seed를 연결하지 않는다.

## 실제 모델 격리 통합 테스트

기본 backend 테스트는 YOLO를 mock 처리해 모델이 없는 CI에서도 실행할 수 있다. 승인 artifact가 `backend/best.pt`에 있고 AI runtime이 설치된 개발 환경에서는 실제 이미지 업로드와 사용자별 이력 API 흐름을 별도의 Django test database로 확인할 수 있다. 테스트 결과 이미지는 OS 임시 디렉터리에 저장하고 테스트 종료 시 제거한다.

Windows PowerShell (`backend` 디렉터리):

```powershell
$env:RUN_LIVE_DETECTION_INTEGRATION = '1'
.\.venv\Scripts\python.exe manage.py test detect.tests.test_live_model_integration
```

POSIX (`backend` 디렉터리):

```bash
RUN_LIVE_DETECTION_INTEGRATION=1 ./.venv/bin/python manage.py test detect.tests.test_live_model_integration
```

이 opt-in 테스트는 capabilities에서 artifact를 사용할 수 있는 상태, 테스트 전용 경로로 모델을 바꿨을 때의 `model_missing`, 정상 경로 복구, 로그인 업로드, DB 저장, 이력 목록·상세 조회 및 다른 사용자의 상세 접근 차단을 검사한다. Django test runner의 test database에만 catalog seed를 실행한다. 실제 Checkpoint를 변경하지 않고, 출처 참고 이미지 한 건의 결과를 모델 성능 점수로 해석하지 않는다. 실행하지 않은 환경에서 이 항목은 `NOT RUN`이며 기본 전체 테스트에서는 skip된다.

## 격리된 실제 브라우저 E2E

`config.e2e_settings`는 별도 환경변수와 고유한 임시 디렉터리가 없으면 시작을 거부한다. Repository 외부에 이번 실행 전용 root를 만들고, 개발 DB 경로와 Media 경로가 겹치지 않게 구성한다. 기존 Media나 DB를 비우거나 이동하지 않는다.

PowerShell에서 임시 root와 marker를 한 번 만든다.

```powershell
$e2eRoot = Join-Path $env:TEMP ("farm-copilot-e2e-" + [guid]::NewGuid().ToString("N"))
[System.IO.Directory]::CreateDirectory($e2eRoot) | Out-Null
New-Item -ItemType Directory -Path (Join-Path $e2eRoot "db"), (Join-Path $e2eRoot "media") | Out-Null
[System.IO.File]::WriteAllText((Join-Path $e2eRoot ".farm-copilot-e2e-root"), "isolated-local-e2e`n", [System.Text.UTF8Encoding]::new($false))
$env:FARM_COPILOT_E2E_MODE = "1"
$env:FARM_COPILOT_E2E_ROOT = $e2eRoot
$env:DJANGO_SETTINGS_MODULE = "config.e2e_settings"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
```

`backend` 디렉터리에서 먼저 검사·마이그레이션·seed·artifact preflight를 실행한 다음에만 서버를 시작한다.

```powershell
.\.venv\Scripts\python.exe manage.py test common.tests.test_e2e_settings_guard --settings=config.settings
.\.venv\Scripts\python.exe manage.py check --settings=config.e2e_settings
.\.venv\Scripts\python.exe manage.py migrate --noinput --settings=config.e2e_settings
.\.venv\Scripts\python.exe manage.py seed_detection_catalog --settings=config.e2e_settings
.\.venv\Scripts\python.exe manage.py check_detection_model --settings=config.e2e_settings
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=config.e2e_settings --noreload
```

진단 이력의 소유권 차단까지 확인하려면 이 서버를 시작하기 전에 테스트 사용자 두 명을 각각 대화형으로 생성한다. 비밀번호는 프롬프트에서만 입력하고 문서나 로그에 기록하지 않는다.

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=config.e2e_settings
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=config.e2e_settings
```

Backend 서버를 실행한 채 별도 PowerShell에서 Frontend를 실행한다.

```powershell
cd ..\frontend
$env:HOST = "127.0.0.1"
$env:PORT = "3000"
$env:BROWSER = "none"
$env:REACT_APP_API_BASE_URL = "http://127.0.0.1:8000"
npm.cmd start
```

설정 검사 전에 각 명령을 별도로 실행한다. `config.e2e_settings`는 Root가 시스템 임시 디렉터리 바로 아래의 새 고유 경로인지, marker가 유효한지, Root 안에 marker와 비어 있는 실제 `db`/`media` 디렉터리만 있는지 검사한다. 기존 Root를 재사용하지 않는다. 검사가 실패하면 원인을 고친 뒤 새 Root로 다시 시작한다. test account와 uploads는 임시 DB/Media에만 만든다. 종료 후 이번 실행에서 만든 서버 프로세스가 멈췄는지 확인하고, 다른 자료가 섞이지 않은 해당 고유 E2E root만 정리한다.

2026-10-20 검증은 저장소에 재실행 가능한 브라우저 테스트 코드가 남아 있지 않은 **도구를 이용한 일회성 Chrome 브라우저 검증(B)** 이다. Chrome에서 로그인, 실제 YOLO 업로드·추론, 결과와 이력 목록/상세, 로그아웃, 타 사용자 접근 차단, 미지원 파일·무탐지·네트워크/모델 미준비 안내를 확인했다. Chrome 모바일 viewport도 확인했으며 실제 모바일 기기나 다른 브라우저는 검증하지 않았다. 검증 결과는 정확도 평가가 아니다.
