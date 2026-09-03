# 농업코파일럿 Local Setup Guide

이 문서는 이 Repository를 처음 Clone한 개발자가 현재 코드 기준으로 Local 환경을
구성하고 검증하기 위한 실행 문서다. 프로젝트 종료 당시의 서비스 아키텍처는
PostgreSQL과 AWS S3를 사용했지만, 현재 포트폴리오 Repository의 기본 Local 경로는
SQLite와 Django `FileSystemStorage`다.

외부 API, OpenAI, AWS credential은 기본 실행에 필요하지 않다. 해당 기능을 사용할
때만 별도로 설정한다. 실제 credential을 Source, 문서 또는 Git에 기록하지 않는다.

## 1. 실행 환경

현재 Repository에는 Node `engines`나 Python `requires-python` 제약이 선언되어 있지
않다. 아래 버전은 2026-09-03에 실제 검증한 환경이다.

| 항목 | 현재 코드/검증 기준 |
|---|---|
| Python | 3.11.9 (`pyproject.toml`의 Ruff target도 `py311`) |
| Django | 5.0.6 |
| Node.js | v22.20.0 |
| npm | 10.9.3 |
| React | 18.3.1 |
| Local DB | SQLite |
| Production DB | PostgreSQL (`psycopg2-binary==2.9.9`) |

Windows PowerShell에서 명령을 검증했다. POSIX에서는 가상환경 실행 파일 경로만
`.venv/bin/python`으로 바꾸면 된다.

선택 기능에는 다음 외부 환경이 추가로 필요하다.

- 토양·비료 분석: Kakao 주소 검색, 농촌진흥청 토양검정 V2·비료사용처방 V2
- 작물 수익 예측: 기상청 ASOS, aT 중도매인 가격정보
- 병해충 진단: 별도 YOLO checkpoint와 AI dependency
- 농업 AI 챗봇: OpenAI API, AI dependency, Chroma index
- Production 저장소: 선택적으로 AWS S3
- 실제 이메일 발송: SMTP

## 2. Repository 구조

```text
.
├── backend/                       # Django project; manage.py 위치
│   ├── config/settings.py         # 단일 settings와 실행 profile 분기
│   ├── requirements.txt           # 기본 Backend dependency
│   ├── requirements-dev.txt       # 기본 dependency + Ruff
│   ├── requirements-ai.txt        # 기본 dependency + YOLO/챗봇 runtime
│   ├── detect/fixtures/model_classes.json
│   └── chatbot/chatbot_source.csv
├── frontend/                      # Create React App 기반 React SPA
│   ├── package.json
│   └── .env.example
└── docs/
```

`backend/best.pt`, `backend/database/`, SQLite DB, `.env`, `frontend/build/`은
Git에서 제외된 Local artifact다. Clone 직후에는 존재한다고 가정하지 않는다.

## 3. Backend 설정

### 3.1 Virtual Environment와 dependency

Repository root에서 다음을 실행한다.

Windows PowerShell:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

POSIX:

```sh
cd backend
python3.11 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

`requirements.txt`만 설치하면 인증, 커뮤니티, Local storage, CSV 기반 목록과
외부 API 연동 코드는 실행할 수 있다. YOLO와 챗봇 runtime은 포함되지 않으며 필요한
경우에만 `requirements-ai.txt`를 설치한다.

### 3.2 Local 환경변수

`backend`에서 example을 복사한다.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

POSIX:

```sh
cp .env.example .env
```

`.env`의 `DJANGO_SECRET_KEY`에는 Local 전용 임의의 긴 값을 설정한다. 빈 값도 Django
import 자체를 막지는 않지만 안전한 실행 설정이 아니다. 생성한 값은 출력물이나 Git에
남기지 않는다. Local 기본 profile에 필요한 핵심 설정은 다음과 같다.

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

`config/settings.py`는 `python-dotenv`로 `backend/.env`를 읽는다. 설정 이름과 전체
기본값은 `backend/.env.example`을 기준으로 편집한다.

환경변수의 코드 기준 분류는 다음과 같다.

| 분류 | 환경변수 |
|---|---|
| Backend 필수 | `DJANGO_SECRET_KEY` |
| Local SQLite profile | `DJANGO_USE_SQLITE=true`, 선택 경로 `SQLITE_DATABASE_PATH` |
| PostgreSQL profile | `DJANGO_USE_SQLITE=false`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` |
| Local origin/cookie | `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_BASE_URL`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`, `CSRF_COOKIE_SAMESITE` |
| HTTPS/Proxy 선택 설정 | `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_SECURE_HSTS_PRELOAD`, `DJANGO_BEHIND_HTTPS_PROXY` |
| 기능 Flag | `SOIL_SERVICE_ENABLED`, `PREDICTION_SERVICE_ENABLED`, `CHATBOT_ENABLED`, `DJANGO_USE_S3` |
| 병해충 진단 선택 설정 | `YOLO_MODEL_PATH`, `YOLO_AUGMENTED_INFERENCE`; `YOLO_CONFIG_DIR`는 Ultralytics runtime 설정 |
| 챗봇 선택 설정 | `OPENAI_API_KEY`, `CHROMA_DB_PATH`, `CHATBOT_SOURCE_CSV`, `CHATBOT_LLM_MODEL`, `CHATBOT_EMBEDDING_MODEL`, `CHATBOT_COLLECTION_NAME` |
| 이메일 선택 설정 | `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_TIMEOUT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` |
| S3 선택 설정 | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_LOCATION` |

`SOIL_SERVICE_ENABLED`와 `PREDICTION_SERVICE_ENABLED`의 example 기본값은 `true`지만,
필요한 API key가 없으면 capability는 `limited`이고 실제 요청은 503 경계로 처리된다.
`CHATBOT_ENABLED`의 기본값은 `false`다.

### 3.3 Database와 migration

Local에서는 별도 DB Server나 사전 DB 생성이 필요 없다. `DJANGO_USE_SQLITE=true`이면
`SQLITE_DATABASE_PATH` 위치의 파일을 사용하며, 기본 example은 `backend/db.sqlite3`다.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

POSIX에서는 `.\.venv\Scripts\python.exe`를 `./.venv/bin/python`으로 바꾼다.

새 Clone의 빈 SQLite DB에는 위 명령이 전체 schema를 생성한다. 기존 Local DB를
사용하는 경우 다음 명령의 종료 코드가 0이어야 모든 migration이 적용된 상태다.

```powershell
.\.venv\Scripts\python.exe manage.py migrate --check
```

PostgreSQL profile에서는 DB와 사용자를 먼저 PostgreSQL에 생성한 후 `.env`의
`DATABASE_*` 값을 채우고 동일한 `manage.py migrate`를 실행한다. Repository에는
PostgreSQL DB 생성 script가 없으므로 임의의 DB 생성 명령을 이 문서에서 지정하지 않는다.

일반 실행에 필수인 fixture는 없다. 병해충 진단을 사용할 때만 migration 후 아래
fixture를 로드한다.

```powershell
.\.venv\Scripts\python.exe manage.py loaddata detect/fixtures/model_classes.json
```

이 fixture는 병해 상세 5건과 YOLO class ID 0~5의 mapping 6건을 포함한다.

Admin을 사용하지 않으면 superuser는 필요하지 않다. 일반 사용자는 Frontend 회원가입으로
생성할 수 있다. Local example은 console email backend를 사용하므로 인증 메일 내용은
Backend terminal에 출력된다. 실제 메일 수신을 검증하려면 SMTP 설정이 별도로 필요하다.

### 3.4 Backend 실행

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

기본 주소는 `http://127.0.0.1:8000`이다. 기능 설정 상태는 credential 값을 노출하지
않는 `GET http://127.0.0.1:8000/api/capabilities/`에서 확인할 수 있다.

## 4. Frontend 설정

새 terminal에서 Repository root를 기준으로 실행한다.

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm start
```

POSIX에서는 환경 파일 복사만 다음과 같이 바꾼다.

```sh
cp .env.example .env
```

Frontend의 API 연결용 사용자 설정 환경변수는 하나다.

```dotenv
REACT_APP_API_BASE_URL=http://localhost:8000
```

값을 생략해도 코드의 fallback은 `http://localhost:8000`이다. 이 밖에 여러
component가 Create React App이 제공하는 `PUBLIC_URL`을 정적 asset URL에 사용한다.
`PUBLIC_URL`은 Repository의 `.env.example`에 없으며 `/`가 아닌 경로에 배포할 때만
검토하는 선택 설정이다. 개발 Server 기본 Port는 3000이며 Browser에서는
`http://localhost:3000`을 연다.

Axios client는 `withCredentials: true`로 Django session cookie를 전송한다. 요청 전에
`csrftoken` cookie가 있으면 `X-CSRFToken` header도 자동으로 붙인다. 따라서 Frontend
origin을 변경하면 Backend의 `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`,
`FRONTEND_BASE_URL`도 같은 origin에 맞춰야 한다.

Production build 명령은 다음과 같다.

```powershell
npm run build
```

출력 위치는 `frontend/build/`이며 Git 추적 대상이 아니다.

## 5. 기본 기능 확인

외부 credential과 AI artifact 없이 확인할 수 있는 범위는 다음과 같다.

- `GET /api/capabilities/`의 기능 상태 확인
- SQLite 기반 인증과 session 처리
- 회원가입, 로그인, 로그아웃과 계정 기능
- 커뮤니티 게시글·댓글 기능과 Local image 저장
- Repository의 CSV를 사용하는 작물명·지역명 등 정적 목록
- 저장된 토양 분석·예측·진단·챗봇 session의 목록/상세/삭제 API

토양/비료 실제 조회와 작물 수익 예측은 외부 API key가 필요하다. 병해충 추론과
챗봇 답변은 각각 별도 artifact/runtime 조건을 모두 만족해야 한다.

## 6. 외부 API 설정

다음 값은 기본 Local 실행에는 선택 설정이며 해당 기능을 사용할 때만 필수다.

| 기능 | 환경변수 | 필수 여부 | 호출 Module / 설명 |
|---|---|---|---|
| Kakao 주소 검색 | `KAKAO_REST_API_KEY` | 토양 기능별 필수 | `soil/services.py`; 주소 검색과 법정동·PNU 구성 |
| 농촌진흥청 토양검정 V2 | `DATA_GO_KR_SOIL_SERVICE_KEY` | 토양 기능별 필수 | `soil/services.py`; `SoilExam/V2/getSoilExamList` |
| 농촌진흥청 비료사용처방 V2 | `DATA_GO_KR_FERTILIZER_V2_SERVICE_KEY` | 비료 기능별 필수 | `soil/services.py`; `SoilEnviron_FrtlzrUse_V2` |
| 기상청 ASOS | `DATA_GO_KR_WEATHER_SERVICE_KEY` | 예측 기능별 필수 | `prediction/services.py`; ASOS 일자료 |
| aT 중도매인 가격정보 | `DATA_GO_KR_MARKET_SERVICE_KEY` | 예측 기능별 필수 | `prediction/services.py`; `B552845/periodWholesale/price` |
| OpenAI | `OPENAI_API_KEY` | 챗봇 기능별 필수 | embedding 생성과 실시간 LLM 답변; 비용 발생 가능 |
| SMTP | `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` 및 `EMAIL_*` | 실제 메일 발송 시 필수 | 회원가입 인증과 비밀번호 재설정 메일 |

토양 관련 세 key는 `SOIL_SERVICE_ENABLED=true`, 예측 관련 두 key는
`PREDICTION_SERVICE_ENABLED=true`일 때 사용된다. Provider별 별도 flag는 없다.

외부 호출 없이 key 설정 여부만 확인하려면 다음 명령을 사용한다.

```powershell
.\.venv\Scripts\python.exe manage.py check_external_services
```

`--live`를 붙인 검사는 실제 Provider 요청을 보낸다. Credential, 호출량과 비용 조건을
확인한 운영자만 필요한 Provider를 명시해 실행한다.

```powershell
.\.venv\Scripts\python.exe manage.py check_external_services --live kakao soil fertilizer weather market
```

## 7. AI 기능 설정

AI 기능 두 개는 `requirements-ai.txt`를 함께 사용한다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ai.txt
```

### 7.1 병해충 진단

기본 checkpoint 예상 위치는 `backend/best.pt`다. 다른 위치를 사용할 때는
`YOLO_MODEL_PATH`에 절대 경로 또는 `backend` 기준 상대 경로를 지정한다.

```dotenv
YOLO_MODEL_PATH=best.pt
YOLO_AUGMENTED_INFERENCE=true
```

`*.pt`는 `.gitignore` 대상이므로 Clone에는 모델이 포함되지 않는다. 별도로 확보한
checkpoint가 다음 class contract와 정확히 일치해야 한다.

| class_id | model label | 연결되는 병해 |
|---:|---|---|
| 0 | 고추 탄저병 | 고추 탄저병 |
| 1 | 고추 흰가루병 | 고추 흰가루병 |
| 2 | 오이 노균병 | 오이 노균병 |
| 3 | 토마토 흰가루병 | 토마토 흰가루병 |
| 4 | 오이 노균병 | 오이 노균병 |
| 5 | 오이 흰가루병 | 오이 흰가루병 |

런타임은 model metadata 전체가 위 mapping과 같지 않으면 추론을 거부한다. DB mapping은
`detect/fixtures/model_classes.json`을 `loaddata`해 준비한다.

필요 dependency는 `torch`, `torchvision`, `ultralytics`, `opencv-python`이며
`requirements-ai.txt`에 고정되어 있다. 코드에서 GPU device를 강제하지 않는다.
현재 검증 환경의 `torch==2.3.1+cpu`, CUDA 미사용 상태에서 checkpoint load와 metadata
검증이 성공했으므로 GPU는 필수가 아니다. 실제 이미지 추론은 이번 Audit에서 실행하지
않았다.

병해충 진단에는 별도 Feature Flag가 없다. capability는 checkpoint 파일 존재 여부를
보고하며, 실제 요청 시 AI dependency·model contract·fixture mapping도 모두 필요하다.

### 7.2 농업 AI 챗봇

Clone에 포함된 기준 source는 `backend/chatbot/chatbot_source.csv`이며 현재 8개 유효 행을
가진다. 형식만 만들 때는 `chatbot/chatbot_source.example.csv`를 참고한다. 필수 열은
`질문`, `답변`, `출처`, `출처URL`이고 `출처URL`은 HTTPS여야 한다.

비용 없이 source만 검증할 수 있다.

```powershell
.\.venv\Scripts\python.exe manage.py build_chatbot_index --source chatbot/chatbot_source.csv --validate-only
```

실제 index 생성은 OpenAI embedding 호출로 비용이 발생한다. 실행 전
`requirements-ai.txt` 설치와 `OPENAI_API_KEY`가 필요하며, output directory는 없거나
비어 있어야 한다.

```powershell
.\.venv\Scripts\python.exe manage.py build_chatbot_index --source chatbot/chatbot_source.csv --output artifacts/chroma
```

생성 후 설정 예시는 다음과 같다.

```dotenv
CHATBOT_ENABLED=true
OPENAI_API_KEY=<openai-api-key>
CHROMA_DB_PATH=artifacts/chroma
CHATBOT_SOURCE_CSV=chatbot/chatbot_source.csv
CHATBOT_LLM_MODEL=gpt-4o-mini
CHATBOT_EMBEDDING_MODEL=text-embedding-3-small
CHATBOT_COLLECTION_NAME=agriculture-knowledge
```

Chroma index는 Git에서 제외된다. 런타임은 `chroma.sqlite3`과
`index-manifest.json`의 존재를 요구하며 manifest의 embedding model, collection,
양수 document count, 64자 source SHA-256 필드를 검사한다. 현재 런타임은 manifest에
기록된 hash를 현재 source CSV와 다시 계산해 비교하지는 않는다.

챗봇 활성 조건은 `CHATBOT_ENABLED=true`, `OPENAI_API_KEY`, AI dependency,
현재 설정과 위 필드가 일치하는 Chroma index다.

## 8. Storage

### 8.1 Local

```dotenv
DJANGO_USE_S3=false
```

이 상태에서는 Django `FileSystemStorage`를 사용한다. `MEDIA_URL`은 `/media/`,
`MEDIA_ROOT`는 `backend/media/`이고 `STATIC_URL`은 `/static/`, `STATIC_ROOT`는
`backend/staticfiles/`다. `DJANGO_DEBUG=true`일 때 Django URL 설정이 Local media를
serve한다. `collectstatic`은 Local `staticfiles`에 정적 파일을 모은다.

### 8.2 AWS S3

프로젝트의 최종 서비스 아키텍처에는 S3가 포함됐지만 Local 실행에는 필수가 아니다.
이미 준비된 bucket과 credential이 있을 때만 활성화한다.

```dotenv
DJANGO_USE_S3=true
AWS_ACCESS_KEY_ID=<aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<aws-secret-access-key>
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_LOCATION=<optional-prefix>
```

S3에서는 static과 기본 media storage를 각각 `static`, `media` prefix에 두며,
게시글과 병해충 ImageField의 전용 storage는 `post_board`, `pest_detection` location을
사용한다. 실제 AWS 연결과 업로드는 이번 Audit에서 검증하지 않았다.

## 9. 테스트 및 검증

다음 명령은 2026-09-03 현재 Repository와 설치되어 있던 dependency에서 직접 실행했다.

Backend (`backend`에서 실행):

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check_external_services
.\.venv\Scripts\python.exe manage.py build_chatbot_index --source chatbot/chatbot_source.csv --validate-only
```

성공 기준은 각각 Python version 출력, broken requirement 없음, system check 0건,
`migrate --check` 종료 코드 0, 전체 test 통과, credential 노출 없는 설정 상태 출력,
CSV 유효 행 수 출력이다. 이번 작업 당시 기존 Local DB의 `migrate --check`만 종료 코드
1이었다. `showmigrations --plan` 결과 `soil.0006_rename_crop_data_cropdata`가 미적용인
것으로 확인했으며 DB를 변경하지 않기 위해 Audit 중 migration을 적용하지 않았다.
Backend test DB에서는 전체 migration과 114개 test가 통과했다.

Frontend (`frontend`에서 실행):

```powershell
node --version
npm --version
npm run lint
npm test -- --watchAll=false --runInBand
npm run build
```

검증 결과 lint는 경고 없이 완료됐고, 28개 suite의 140개 test가 모두 통과했으며,
production build가 `Compiled successfully`로 완료됐다.

## 10. Production 관련 참고

Production에서는 코드상 PostgreSQL, HTTPS 보안 설정, SMTP가 요구되며 S3 또는
persistent Local volume 중 하나를 운영자가 준비해야 한다. 상세 checklist는
[`reference/backend/DEPLOYMENT.md`](reference/backend/DEPLOYMENT.md)를 참고하되,
해당 문서의 현재 불일치는 아래 Troubleshooting 항목을 우선 적용한다.

## 11. Troubleshooting

### `migrate --check`가 종료 코드 1을 반환한다

```powershell
.\.venv\Scripts\python.exe manage.py showmigrations --plan
```

미적용 항목을 확인한 뒤 보존이 필요한 DB인지 먼저 판단하고, 정상적인 Local 초기 설정
과정이라면 `manage.py migrate`를 실행한다. 이번 Audit의 기존 Local DB에는
`soil.0006_rename_crop_data_cropdata`가 미적용이었다.

### 병해충 기능이 `limited`이거나 요청이 503이다

공개 Clone에는 `best.pt`가 없다. `YOLO_MODEL_PATH`의 파일, AI dependency, 정확한 6개
model class metadata, `model_classes.json` fixture load를 모두 확인한다.

### 챗봇을 켰지만 사용할 수 없다

`CHATBOT_ENABLED=true`만으로는 충분하지 않다. `OPENAI_API_KEY`, AI dependency,
`chroma.sqlite3`과 유효한 `index-manifest.json`, embedding model과 collection 설정을
함께 확인한다.

### 로그인 후 POST/PATCH/DELETE가 CSRF 또는 CORS로 실패한다

Frontend URL과 `REACT_APP_API_BASE_URL`, `CORS_ALLOWED_ORIGINS`,
`CSRF_TRUSTED_ORIGINS`, `FRONTEND_BASE_URL`이 각각 Frontend/Backend 실제 origin과
일치하는지 확인한다. Local HTTP에서는 example처럼 secure cookie 설정을 `false`로 둔다.

### Production Gunicorn module을 찾지 못한다

현재 WSGI module은 `config.wsgi:application`이다. 과거 문서의
`aivle_big.wsgi:application`은 현재 코드와 일치하지 않는다.
