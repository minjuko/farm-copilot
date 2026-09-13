# 농업코파일럿 Local Setup Guide

이 문서는 Repository를 처음 Clone한 개발자가 **현재 코드를 기준으로 Local 환경을 구성하고 검증하기 위한 실행 가이드**입니다.

프로젝트 최종 서비스 아키텍처는 PostgreSQL과 AWS S3를 사용했으며, 현재 포트폴리오 Repository의 기본 Local 실행 환경은 **SQLite와 Django `FileSystemStorage`**입니다.

외부 API, OpenAI, AWS Credential은 기본 실행에 필요하지 않으며 해당 기능을 사용할 때만 별도로 설정합니다. 실제 Credential은 Source Code, 문서 또는 Git에 기록하지 않습니다.

---

## 1. 실행 환경

현재 Repository에는 Node `engines`나 Python `requires-python` 제약이 선언되어 있지 않습니다.

아래 버전은 **2026-09-03에 실제 검증한 환경**이며 최소 지원 버전을 의미하지 않습니다.

| 항목 | 검증 환경 |
| --- | --- |
| Python | 3.11.9 |
| Django | 5.0.6 |
| Node.js | v22.20.0 |
| npm | 10.9.3 |
| React | 18.3.1 |
| Local Database | SQLite |
| Production Database | PostgreSQL (`psycopg2-binary==2.9.9`) |

Python 3.11.9는 `pyproject.toml`의 Ruff target인 `py311`과도 일치합니다.

명령은 Windows PowerShell에서 검증했습니다. POSIX 환경에서는 가상환경 Python 경로를 `.venv/bin/python`으로 변경해 사용할 수 있습니다.

### 선택 기능별 추가 요구사항

| 기능 | 추가 요구사항 |
| --- | --- |
| 토양검정 · 비료 처방 | Kakao 주소 검색 · 농촌진흥청 토양검정 V2 · 비료사용처방 V2 Credential |
| 농작물 수익 분석 | 기상청 ASOS · aT 중도매인 가격정보 Credential |
| AI 병해충 진단 | YOLO Checkpoint · AI Dependency · Class Mapping |
| 농업 AI 챗봇 | OpenAI API · AI Dependency · Chroma Index |
| Production Storage | AWS S3 설정 |
| 실제 이메일 발송 | SMTP 설정 |

---

## 2. Repository 구조

실행과 환경 구성에 필요한 주요 파일은 다음과 같습니다.

```text
.
├── backend/
│   ├── config/
│   │   └── settings.py
│   ├── detect/
│   │   └── fixtures/
│   │       └── model_classes.json
│   ├── chatbot/
│   │   └── chatbot_source.csv
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── requirements-ai.txt
│   ├── .env.example
│   └── manage.py
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── .env.example
│
└── docs/
    ├── SETUP.md
    └── reference/
```

다음 파일과 디렉터리는 Local Artifact이며 Git에서 제외됩니다.

```text
backend/best.pt
backend/database/
backend/db.sqlite3
backend/.env
backend/media/
frontend/.env
frontend/build/
```

따라서 새로 Clone한 Repository에는 존재한다고 가정하지 않습니다.

---

# 3. Backend 설정

## 3.1 Virtual Environment와 Dependency

Repository Root에서 Backend 디렉터리로 이동한 뒤 가상환경을 구성합니다.

### Windows PowerShell

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### POSIX

```bash
cd backend
python3.11 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

`requirements.txt`에는 기본 Backend 실행에 필요한 Dependency가 포함되어 있습니다.

이를 통해 다음 범위를 실행할 수 있습니다.

- 회원 · 인증
- 커뮤니티
- Local Storage
- CSV 기반 목록
- 외부 API 연동 코드

YOLO와 농업 AI 챗봇 Runtime은 기본 Dependency에 포함되지 않습니다.

해당 기능을 실행할 때만 `requirements-ai.txt`를 추가로 설치합니다.

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ai.txt
```

### POSIX

```bash
./.venv/bin/python -m pip install -r requirements-ai.txt
```

개발 도구가 필요한 경우에는 `requirements-dev.txt`를 사용할 수 있습니다.

---

## 3.2 Local 환경변수

`backend` 디렉터리에서 `.env.example`을 복사합니다.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### POSIX

```bash
cp .env.example .env
```

Local 실행을 위한 기본 설정 예시는 다음과 같습니다.

```dotenv
DJANGO_SECRET_KEY=<local-random-secret>

DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DJANGO_USE_SQLITE=true
SQLITE_DATABASE_PATH=db.sqlite3

DJANGO_USE_S3=false

CORS_ALLOWED_ORIGINS=http://localhost:3000
CSRF_TRUSTED_ORIGINS=http://localhost:3000
FRONTEND_BASE_URL=http://localhost:3000

SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax

DJANGO_SECURE_SSL_REDIRECT=false
```

`DJANGO_SECRET_KEY`에는 Local 전용 임의의 긴 값을 설정합니다.

빈 값도 Django Import 자체를 막지는 않지만 안전한 실행 설정은 아닙니다. 생성한 값은 Terminal 출력, 문서 또는 Git에 기록하지 않습니다.

`config/settings.py`는 `python-dotenv`를 통해 `backend/.env`를 읽습니다. 전체 설정 이름과 기본값은 `backend/.env.example`을 기준으로 확인합니다.

### 환경변수 분류

| 분류 | 환경변수 |
| --- | --- |
| Backend 필수 | `DJANGO_SECRET_KEY` |
| Local SQLite | `DJANGO_USE_SQLITE`, `SQLITE_DATABASE_PATH` |
| PostgreSQL | `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` |
| Local Origin · Cookie | `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_BASE_URL`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`, `CSRF_COOKIE_SAMESITE` |
| HTTPS · Proxy | `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_SECURE_HSTS_PRELOAD`, `DJANGO_BEHIND_HTTPS_PROXY` |
| 기능 Flag | `SOIL_SERVICE_ENABLED`, `PREDICTION_SERVICE_ENABLED`, `CHATBOT_ENABLED`, `DJANGO_USE_S3` |
| 병해충 진단 | `YOLO_MODEL_PATH`, `YOLO_AUGMENTED_INFERENCE` |
| 챗봇 | `OPENAI_API_KEY`, `CHROMA_DB_PATH`, `CHATBOT_SOURCE_CSV`, `CHATBOT_LLM_MODEL`, `CHATBOT_EMBEDDING_MODEL`, `CHATBOT_COLLECTION_NAME` |
| 이메일 | `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_TIMEOUT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` |
| AWS S3 | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_LOCATION` |

`YOLO_CONFIG_DIR`는 `.env.example`에 포함되어 있지만 Application Code가 직접 읽는 값이 아니라 Ultralytics Runtime 설정입니다.

`SOIL_SERVICE_ENABLED`와 `PREDICTION_SERVICE_ENABLED`의 Example 기본값은 `true`입니다. 필요한 API Key가 없으면 Capability는 `limited`이며 실제 요청은 503 경계로 처리됩니다.

`CHATBOT_ENABLED`의 기본값은 `false`입니다.

병해충 진단에는 별도의 Feature Flag가 없습니다.

---

## 3.3 Database와 Migration

### Local — SQLite

기본 Local 실행에서는 별도 Database Server를 준비할 필요가 없습니다.

```dotenv
DJANGO_USE_SQLITE=true
SQLITE_DATABASE_PATH=db.sqlite3
```

새 Clone에서 다음 명령을 실행하면 SQLite Database와 전체 Schema가 생성됩니다.

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

### POSIX

```bash
./.venv/bin/python manage.py migrate
```

기존 Local DB를 사용하는 경우 모든 Migration 적용 여부를 다음 명령으로 확인할 수 있습니다.

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe manage.py migrate --check
```

### POSIX

```bash
./.venv/bin/python manage.py migrate --check
```

종료 코드가 `0`이면 모든 Migration이 적용된 상태입니다.

> **Audit 참고**
>
> 2026-09-03 검증 당시 기존 Local SQLite DB에는 `soil.0006_rename_crop_data_cropdata` Migration이 적용되지 않은 상태였습니다. 기존 DB를 변경하지 않는 Audit 원칙에 따라 해당 Migration은 적용하지 않았습니다.
>
> Backend Test DB에서는 전체 Migration 적용 후 114개 Test가 정상 통과했습니다.

### PostgreSQL

PostgreSQL Profile을 사용하려면:

```dotenv
DJANGO_USE_SQLITE=false

DATABASE_NAME=<database-name>
DATABASE_USER=<database-user>
DATABASE_PASSWORD=<database-password>
DATABASE_HOST=<database-host>
DATABASE_PORT=<database-port>
```

를 설정합니다.

Database와 사용자는 PostgreSQL에 사전에 준비되어 있어야 하며, 이후 동일하게:

```bash
python manage.py migrate
```

를 실행합니다.

Repository에는 PostgreSQL Database 생성 Script가 없으므로 특정 생성 명령을 이 문서에서 가정하지 않습니다.

---

## 3.4 Fixture

일반 Local 실행에 필수인 Fixture는 없습니다.

AI 병해충 진단을 사용할 때만 Migration 이후 다음 Fixture를 Load합니다.

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe manage.py loaddata detect/fixtures/model_classes.json
```

### POSIX

```bash
./.venv/bin/python manage.py loaddata detect/fixtures/model_classes.json
```

이 Fixture에는:

- 병해 상세 5건
- YOLO Class ID 0~5 Mapping 6건

이 포함되어 있습니다.

Admin을 사용하지 않는다면 Superuser는 필요하지 않습니다. 일반 사용자는 Frontend 회원가입을 통해 생성할 수 있습니다.

Local Example은 Console Email Backend를 사용하므로 이메일 내용은 Backend Terminal에 출력됩니다. 실제 이메일 수신을 확인하려면 별도 SMTP 설정이 필요합니다.

---

## 3.5 Backend 실행

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

### POSIX

```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py runserver
```

기본 Backend 주소:

```text
http://127.0.0.1:8000
```

현재 기능 설정 상태는 Credential 값을 노출하지 않는 다음 Endpoint에서 확인할 수 있습니다.

```text
GET http://127.0.0.1:8000/api/capabilities/
```

Capability는 기능별 설정 상태를 확인하기 위한 정보입니다. 특히 병해충 진단은 Checkpoint 존재 여부를 기준으로 상태를 보고하므로 **실제 추론 가능 여부 전체를 보장하지 않습니다.**

---

# 4. Frontend 설정

새 Terminal에서 `frontend` 디렉터리로 이동합니다.

### Windows PowerShell

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm start
```

### POSIX

```bash
cd frontend
npm ci
cp .env.example .env
npm start
```

Frontend에서 직접 설정하는 Backend API 환경변수는 다음과 같습니다.

```dotenv
REACT_APP_API_BASE_URL=http://localhost:8000
```

설정하지 않아도 코드의 기본값은:

```text
http://localhost:8000
```

입니다.

개발 Server 기본 주소:

```text
http://localhost:3000
```

일부 Component는 Create React App에서 제공하는 `PUBLIC_URL`을 정적 Asset URL에 사용합니다.

`PUBLIC_URL`은 Repository의 `.env.example`에 포함되어 있지 않으며, `/`가 아닌 경로에 배포할 때 검토하는 선택 설정입니다.

---

## 4.1 Session · CSRF · CORS

Axios Client는:

```text
withCredentials: true
```

를 사용해 Django Session Cookie를 Backend 요청에 전달합니다.

`csrftoken` Cookie가 존재하면 요청 전에 `X-CSRFToken` Header도 자동으로 추가합니다.

따라서 Frontend Origin을 변경하면 Backend의 다음 설정도 실제 Frontend Origin에 맞춰야 합니다.

```text
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
FRONTEND_BASE_URL
```

Local HTTP 환경에서는:

```dotenv
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

로 설정합니다.

---

## 4.2 Production Build

```bash
npm run build
```

Build 결과는:

```text
frontend/build/
```

에 생성되며 Git 추적 대상이 아닙니다.

---

# 5. 기본 기능 확인

외부 Credential과 AI Artifact 없이 확인할 수 있는 범위는 다음과 같습니다.

- `/api/capabilities/` 기능 상태 확인
- SQLite 기반 회원 · 인증 · Session 처리
- 회원가입 · 로그인 · 로그아웃 및 계정 기능
- 커뮤니티 게시글 · 댓글
- Local Image 저장
- Repository CSV 기반 작물명 · 지역명 등 정적 목록
- 기존에 저장된 분석·진단·챗봇 데이터의 목록 · 상세 · 삭제 API

다음 기능의 실제 요청에는 추가 설정이 필요합니다.

| 기능 | 필요한 추가 설정 |
| --- | --- |
| 토양검정 · 비료 처방 | 외부 API Credential |
| 농작물 수익 분석 | 외부 API Credential |
| AI 병해충 진단 | YOLO Checkpoint · AI Dependency · Fixture |
| 농업 AI 챗봇 | OpenAI · AI Dependency · Chroma Index |

---

# 6. 외부 API 설정

다음 Credential은 기본 Local 실행에는 필요하지 않으며 해당 기능을 사용할 때만 설정합니다.

| 기능 | 환경변수 | 사용 위치 · 목적 |
| --- | --- | --- |
| Kakao 주소 검색 | `KAKAO_REST_API_KEY` | `soil/services.py` · 주소 검색 및 법정동·PNU 구성 |
| 농촌진흥청 토양검정 V2 | `DATA_GO_KR_SOIL_SERVICE_KEY` | `soil/services.py` · 토양 화학성 조회 |
| 농촌진흥청 비료사용처방 V2 | `DATA_GO_KR_FERTILIZER_V2_SERVICE_KEY` | `soil/services.py` · 비료사용처방 조회 |
| 기상청 ASOS | `DATA_GO_KR_WEATHER_SERVICE_KEY` | `prediction/services.py` · 기상 데이터 |
| aT 중도매인 가격정보 | `DATA_GO_KR_MARKET_SERVICE_KEY` | `prediction/services.py` · 시장가격 데이터 |
| OpenAI | `OPENAI_API_KEY` | Embedding 생성 · 챗봇 LLM 응답 |
| SMTP | `EMAIL_*` | 회원가입 인증 · 비밀번호 재설정 메일 |

토양 관련 API는:

```dotenv
SOIL_SERVICE_ENABLED=true
```

수익 분석 관련 API는:

```dotenv
PREDICTION_SERVICE_ENABLED=true
```

일 때 사용합니다.

Provider별 별도 Feature Flag는 없습니다.

---

## 6.1 외부 서비스 설정 확인

실제 Provider 호출 없이 Credential 설정 여부만 확인할 수 있습니다.

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe manage.py check_external_services
```

### POSIX

```bash
./.venv/bin/python manage.py check_external_services
```

`--live` 옵션은 실제 외부 Provider 요청을 수행합니다.

Credential, 호출량, 비용 조건을 확인한 경우에만 필요한 Provider를 지정해 실행합니다.

```bash
python manage.py check_external_services --live kakao soil fertilizer weather market
```

> 외부 서비스별 마지막 실제 호출 검증 결과와 검증 시점은 [`reference/API_STATUS.md`](./reference/API_STATUS.md)에 별도로 기록합니다.

---

# 7. AI 기능 설정

AI 병해충 진단과 농업 AI 챗봇은 기본 Backend Dependency 외에 `requirements-ai.txt`가 필요합니다.

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ai.txt
```

### POSIX

```bash
./.venv/bin/python -m pip install -r requirements-ai.txt
```

---

## 7.1 AI 병해충 진단

### YOLO Checkpoint

기본 Checkpoint 예상 위치:

```text
backend/best.pt
```

다른 위치를 사용할 경우:

```dotenv
YOLO_MODEL_PATH=<checkpoint-path>
```

를 설정합니다.

기본 예:

```dotenv
YOLO_MODEL_PATH=best.pt
YOLO_AUGMENTED_INFERENCE=true
```

`*.pt` 파일은 `.gitignore` 대상이므로 공개 Clone에는 Model이 포함되지 않습니다.

---

### Model Class Contract

사용하는 Checkpoint는 다음 Class Metadata와 **정확히 일치해야 합니다.**

| class_id | Model Label | 연결되는 병해 |
| ---: | --- | --- |
| 0 | 고추 탄저병 | 고추 탄저병 |
| 1 | 고추 흰가루병 | 고추 흰가루병 |
| 2 | 오이 노균병 | 오이 노균병 |
| 3 | 토마토 흰가루병 | 토마토 흰가루병 |
| 4 | 오이 노균병 | 오이 노균병 |
| 5 | 오이 흰가루병 | 오이 흰가루병 |

Runtime은 Model Metadata 전체가 위 Mapping과 일치하지 않으면 추론을 거부합니다.

Database Mapping은 다음 Fixture로 준비합니다.

```bash
python manage.py loaddata detect/fixtures/model_classes.json
```

---

### Runtime

필요한 주요 Dependency:

```text
torch
torchvision
ultralytics
opencv-python
```

는 `requirements-ai.txt`에 포함되어 있습니다.

코드에서 GPU Device를 강제하지 않습니다.

2026-09-03 검증 환경에서는:

```text
torch==2.3.1+cpu
CUDA 미사용
```

상태로 Checkpoint Load와 Class Metadata 검증이 성공했습니다.

따라서 **GPU는 필수가 아닙니다.**

다만 이번 최종 Audit에서는 실제 이미지를 사용한 YOLO 추론을 다시 실행하지 않았습니다.

병해충 진단에는 별도의 Feature Flag가 없습니다.

`/api/capabilities/`는 Checkpoint 파일 존재 여부를 중심으로 상태를 판단하며 실제 요청에는 다음 조건이 모두 필요합니다.

- AI Dependency
- YOLO Checkpoint
- 정확한 Model Class Contract
- `model_classes.json` Fixture Mapping

---

## 7.2 농업 AI 챗봇

Clone에 포함된 기준 Source:

```text
backend/chatbot/chatbot_source.csv
```

현재 Source에는 8개의 유효한 데이터 행이 있습니다.

형식 참고 파일:

```text
backend/chatbot/chatbot_source.example.csv
```

필수 Column:

```text
질문
답변
출처
출처URL
```

`출처URL`은 HTTPS URL이어야 합니다.

---

### Source 검증

OpenAI 호출 없이 Source 데이터 형식만 검증할 수 있습니다.

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe manage.py build_chatbot_index --source chatbot/chatbot_source.csv --validate-only
```

### POSIX

```bash
./.venv/bin/python manage.py build_chatbot_index --source chatbot/chatbot_source.csv --validate-only
```

---

### Chroma Index 생성

실제 Index 생성은 OpenAI Embedding API를 호출하므로 비용이 발생할 수 있습니다.

실행 전에 다음이 필요합니다.

- `requirements-ai.txt`
- `OPENAI_API_KEY`
- 유효한 Source CSV
- 비어 있거나 존재하지 않는 Output Directory

예:

```bash
python manage.py build_chatbot_index \
  --source chatbot/chatbot_source.csv \
  --output artifacts/chroma
```

생성 후 환경변수 예시는 다음과 같습니다.

```dotenv
CHATBOT_ENABLED=true
OPENAI_API_KEY=<openai-api-key>

CHROMA_DB_PATH=artifacts/chroma
CHATBOT_SOURCE_CSV=chatbot/chatbot_source.csv

CHATBOT_LLM_MODEL=gpt-4o-mini
CHATBOT_EMBEDDING_MODEL=text-embedding-3-small
CHATBOT_COLLECTION_NAME=agriculture-knowledge
```

생성된 Chroma Index는 Git에서 제외됩니다.

Runtime은 다음을 확인합니다.

- `chroma.sqlite3` 존재
- `index-manifest.json` 존재
- Embedding Model 일치
- Collection 일치
- 양수 Document Count
- 64자 Source SHA-256 값 존재

> 현재 Runtime은 Manifest에 기록된 Source SHA-256 값의 존재와 형식을 확인하지만, **현재 `chatbot_source.csv`의 Hash를 다시 계산해 Manifest와 비교하지는 않습니다.**
>
> 따라서 Manifest 검증은 현재 Source와 Index가 완전히 동일한 데이터에서 생성됐음을 Runtime 수준에서 증명하는 검증은 아닙니다.

챗봇을 실제로 사용하려면 다음 조건을 모두 만족해야 합니다.

- `CHATBOT_ENABLED=true`
- `OPENAI_API_KEY`
- AI Dependency
- 유효한 Chroma Index
- 현재 설정과 일치하는 Embedding Model · Collection

---

# 8. Storage

## 8.1 Local Storage

```dotenv
DJANGO_USE_S3=false
```

Local에서는 Django `FileSystemStorage`를 사용합니다.

```text
MEDIA_URL  = /media/
MEDIA_ROOT = backend/media/

STATIC_URL  = /static/
STATIC_ROOT = backend/staticfiles/
```

`DJANGO_DEBUG=true`일 때 Django URL 설정이 Local Media를 제공합니다.

`collectstatic`을 실행하면 정적 파일은 `backend/staticfiles/`에 수집됩니다.

---

## 8.2 AWS S3

프로젝트 최종 서비스 아키텍처에는 AWS S3가 포함되지만 **현재 Local 실행에는 필수가 아닙니다.**

이미 준비된 Bucket과 Credential이 있을 때만 활성화합니다.

```dotenv
DJANGO_USE_S3=true

AWS_ACCESS_KEY_ID=<aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<aws-secret-access-key>
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_LOCATION=<optional-prefix>
```

S3 사용 시:

- Static → `static`
- 기본 Media → `media`
- 게시글 이미지 → `post_board`
- 병해충 이미지 → `pest_detection`

Location을 사용합니다.

> 2026-09-03 최종 Audit에서는 실제 AWS S3 연결과 Upload를 다시 검증하지 않았습니다.

---

# 9. 테스트 및 검증

다음 명령은 **2026-09-03 현재 Repository와 당시 설치된 Dependency를 기준으로 직접 검증**했습니다.

## 9.1 Backend

`backend` 디렉터리에서 실행합니다.

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check_external_services
.\.venv\Scripts\python.exe manage.py build_chatbot_index --source chatbot/chatbot_source.csv --validate-only
```

### 검증 결과

| 검증 | 결과 |
| --- | --- |
| Python | 3.11.9 |
| `pip check` | Broken Requirement 없음 |
| Django System Check | Issue 0건 |
| Backend Tests | **114 PASS** |
| 외부 서비스 설정 검사 | PASS |
| Chatbot Source 검증 | 8개 유효 행 PASS |
| YOLO Checkpoint Load | PASS |
| YOLO Class Metadata | 6개 Class 일치 |
| Torch Runtime | CPU 환경 Load PASS |
| Chroma Runtime | 기존 Local Index · Manifest 사용 가능 |

### Migration 참고

기존 Local SQLite DB에 대해서만:

```text
manage.py migrate --check
```

가 종료 코드 `1`을 반환했습니다.

`showmigrations --plan` 결과:

```text
soil.0006_rename_crop_data_cropdata
```

가 미적용 상태였습니다.

Audit에서는 기존 DB를 변경하지 않았습니다.

Backend Test DB에서는 전체 Migration 적용 후 **114개 Test가 정상 통과**했습니다.

---

## 9.2 Frontend

`frontend` 디렉터리에서 실행합니다.

```bash
node --version
npm --version
npm run lint
npm test -- --watchAll=false --runInBand
npm run build
```

### 검증 결과

| 검증 | 결과 |
| --- | --- |
| Node.js | v22.20.0 |
| npm | 10.9.3 |
| Frontend Lint | PASS |
| Test Suites | **28 / 28 PASS** |
| Tests | **140 / 140 PASS** |
| Production Build | **PASS** |

Production Build는 `Compiled successfully`로 완료됐습니다.

---

## 9.3 이번 최종 Audit에서 실행하지 않은 검증

다음 작업은 Credential, 비용, 외부 서비스 상태 또는 기존 환경 변경 방지를 위해 이번 Audit에서 다시 실행하지 않았습니다.

- Dependency 재설치 검증 (`pip install`, `npm ci`)
- 기존 Local SQLite DB Migration 적용
- Fixture 실제 Load
- PostgreSQL DB 생성 · 연결
- Backend / Frontend Server 기동 및 Browser 수동 검사
- Kakao · 공공데이터 Provider Live 호출
- SMTP 실제 발송
- OpenAI Embedding · Index 재생성
- OpenAI 챗봇 실제 응답 호출
- YOLO 실제 이미지 추론
- AWS S3 연결 · Upload
- Production 배포

외부 API의 과거 실제 호출 검증 결과와 검증 시점은 [`reference/API_STATUS.md`](./reference/API_STATUS.md)를 참고합니다.

---

# 10. Production 관련 참고

Production 환경에서는 코드 기준으로 다음 설정을 검토해야 합니다.

- PostgreSQL
- HTTPS 보안 설정
- SMTP
- Persistent Media Storage
- 필요 시 AWS S3
- Production Origin에 맞는 CORS · CSRF 설정
- Production용 Cookie 보안 설정

상세 배포 Checklist는 [`reference/backend/DEPLOYMENT.md`](./reference/backend/DEPLOYMENT.md)를 참고할 수 있습니다.

> **현재 코드 기준 WSGI Module은 `config.wsgi:application`입니다.**
>
> 과거 Deployment 문서에 남아 있는 `aivle_big.wsgi:application`은 현재 Repository 구조와 일치하지 않으므로 현재 코드의 Module을 우선합니다.

---

# 11. Troubleshooting

## `migrate --check`가 종료 코드 1을 반환합니다

적용되지 않은 Migration을 확인합니다.

```bash
python manage.py showmigrations --plan
```

미적용 항목을 확인한 뒤 기존 DB의 보존 필요 여부를 먼저 판단합니다.

새 Local 환경의 정상적인 초기 설정 과정이라면:

```bash
python manage.py migrate
```

를 실행합니다.

2026-09-03 Audit 당시 기존 Local SQLite DB에는:

```text
soil.0006_rename_crop_data_cropdata
```

가 미적용 상태였습니다.

---

## 병해충 기능이 `limited`이거나 요청이 503입니다

공개 Clone에는 `best.pt`가 포함되지 않습니다.

다음을 순서대로 확인합니다.

1. `YOLO_MODEL_PATH`가 실제 Checkpoint를 가리키는지
2. `requirements-ai.txt`가 설치되어 있는지
3. Model Metadata가 정의된 6개 Class Contract와 일치하는지
4. `detect/fixtures/model_classes.json`이 Database에 Load되어 있는지

`/api/capabilities/`의 상태만으로 실제 추론 Runtime 전체가 준비됐다고 판단하지 않습니다.

---

## 챗봇을 활성화했지만 사용할 수 없습니다

`CHATBOT_ENABLED=true`만으로는 충분하지 않습니다.

다음을 함께 확인합니다.

- `OPENAI_API_KEY`
- `requirements-ai.txt`
- `chroma.sqlite3`
- `index-manifest.json`
- `CHATBOT_EMBEDDING_MODEL`
- `CHATBOT_COLLECTION_NAME`

현재 Runtime 설정과 Index Manifest가 일치해야 합니다.

---

## 로그인 후 POST · PATCH · DELETE 요청이 CSRF 또는 CORS 오류로 실패합니다

다음 값을 확인합니다.

```text
Frontend 실제 URL
REACT_APP_API_BASE_URL
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
FRONTEND_BASE_URL
```

Frontend와 Backend의 실제 Origin이 각 설정과 일치해야 합니다.

Local HTTP에서는:

```dotenv
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

를 사용합니다.

---

## Production에서 Gunicorn WSGI Module을 찾지 못합니다

현재 WSGI Module은:

```text
config.wsgi:application
```

입니다.

과거 문서의:

```text
aivle_big.wsgi:application
```

은 현재 Repository 구조와 일치하지 않습니다.

현재 코드를 기준으로 실행합니다.
