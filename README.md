# 농업코파일럿 — 꾼꾼농사꾼

> 초보 농업인의 작물 선택과 영농 판단을 돕기 위해 수익 분석, 병해충 진단, 토양검정, 커뮤니티와 상담 화면을 제공하는 웹 서비스입니다.

[![CI](https://github.com/minjuko/farm-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/minjuko/farm-copilot/actions/workflows/ci.yml)

이 서비스는 2024년 KT AIVLE School 5기 Big Project에서 6명이 함께 개발했습니다. 당시 프로젝트명은 **꾼꾼농사꾼**이며 Collaboration상을 받았습니다. 이 저장소는 팀 프로젝트 코드와 2026년 개인적으로 수행한 실행 복구·보안·테스트·문서 개선을 함께 보존합니다. 두 작업의 범위는 아래와 [포트폴리오 근거 문서](docs/FC10_PORTFOLIO_EVIDENCE.md)에 구분해 기록했습니다.

## 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 팀 프로젝트 기간 | 2024.06.17–2024.07.30 |
| 팀 구성 | 6명 — 프론트엔드 2 · 백엔드 2 · AI/Server 2 |
| 프로젝트 자료에 기록된 본인 역할 | 프론트엔드 — 공통 UI, 인증·커뮤니티, 주요 기능 화면과 API 연결 |
| 수상 | KT AIVLE School 5기 Big Project Collaboration상 |
| 원본 저장소 | [프론트엔드](https://github.com/kt-bigproject28/kunkunnongsakun) · [백엔드](https://github.com/kt-bigproject28/bigproject28) |

역할 설명은 당시 프로젝트 자료에 기록된 담당 범위입니다. 백엔드와 AI 모델 구현은 팀 차원의 기능이며, 이 문서는 이를 개인 개발 기여로 주장하지 않습니다.

## 주요 기능

| 기능 | 흐름과 현재 경계 |
| --- | --- |
| 농작물 수익 분석 | 작물·지역·재배 조건 입력 후 가격·기상 자료를 사용해 결과와 이력을 확인합니다. Provider 자격 증명과 연결 상태에 따라 사용할 수 있으며 실제 운영 API 연동은 이번 검증에서 하지 않았습니다. |
| 병해충 진단 | 이미지 업로드, YOLO 결과와 사용자별 이력을 제공합니다. 모델 runtime과 체크포인트가 있어야 진단할 수 있습니다. 공개 clone 기본 CI는 모델을 내려받거나 추론하지 않습니다. |
| 토양검정·비료 처방 | 주소와 필지를 선택하고 토양검정 결과 및 작물별 처방을 조회합니다. 외부 서비스 자격 증명이 필요합니다. |
| 농업 커뮤니티 | 게시글과 댓글을 작성·조회·수정·삭제합니다. |
| 회원·마이페이지 | 회원가입, 세션 로그인, 계정과 사용자 활동을 관리합니다. |
| 농업 챗봇 | RAG 상담 UI와 API가 있습니다. 기본 비활성화이며 운영자 설정, OpenAI 키와 로컬 Chroma 인덱스가 필요합니다. 외부 LLM 호출은 사용자 질문을 전달할 수 있습니다. |

## 화면

<table>
  <tr>
    <th width="50%">메인 화면</th>
    <th width="50%">농작물 수익 분석</th>
  </tr>
  <tr>
    <td align="center"><img src="./docs/readme/01_main.png" alt="농업코파일럿 메인 화면" width="320" /></td>
    <td align="center"><img src="./docs/readme/02_prediction_result.png" alt="농작물 수익 분석 결과 화면" width="320" /></td>
  </tr>
  <tr>
    <th>토양검정·비료 처방</th>
    <th>병해충 진단</th>
  </tr>
  <tr>
    <td align="center"><img src="./docs/readme/03_soil_fertilizer.png" alt="토양검정 및 비료 처방 화면" width="320" /></td>
    <td align="center"><img src="./docs/readme/05_pest_detection.png" alt="병해충 진단 결과 화면" width="320" /></td>
  </tr>
</table>

이미지는 팀 프로젝트 최종 시연 자료를 바탕으로 구성했습니다.

## 기술 구성

| 영역 | 현재 코드에서 확인한 기술 |
| --- | --- |
| 웹 화면 | React 18, JavaScript, React Router 6, Axios, styled-components, Chart.js, Create React App (`react-scripts` 5) |
| 서버 API | Python 3.11 환경, Django 5 JSON views, 세션·CSRF 인증 |
| 로컬 데이터·파일 | SQLite, Django filesystem storage |
| 설정으로 지원하는 선택 구성 | PostgreSQL, S3 (실제 운영 연결·버킷 정책은 검증하지 않음) |
| 분석·AI 선택 runtime | scikit-learn ElasticNet, YOLOv8, PyTorch; YOLO 의존성은 별도 `requirements-ai.txt` |
| 챗봇 선택 runtime | LangChain, Chroma, OpenAI; 기본 비활성화, 실제 유료 호출 미검증 |
| 외부 자료 연동 코드 | Kakao 주소, aT 가격, 기상청 ASOS, 농촌진흥청 토양검정·비료 처방 API |
| 자동화 | Jest, React Testing Library, Playwright Chromium, axe-core, Ruff, GitHub Actions |

서버 endpoint는 Django view와 `JsonResponse`를 사용합니다. Django REST Framework는 dependency/settings에 있으나 현재 앱에서 DRF view·serializer·router를 사용하지 않아 활성 API 기술로 나열하지 않았습니다. 외부 자료 Provider와 PostgreSQL/S3는 코드의 연동·설정 지원을 확인한 것이며 실제 운영 연결을 의미하지 않습니다.

## 아키텍처

```text
React Browser
  └─ Axios (session cookie + CSRF)
       └─ Django JSON views
            ├─ SQLite / filesystem (local default)
            ├─ configured PostgreSQL / S3 (not live-verified)
            └─ optional YOLO, agriculture providers, RAG/OpenAI
```

진단 이미지는 비공개 저장소에 보관하며 로그인 사용자만 인증 Django 이미지 endpoint로 조회합니다. 목록·상세·삭제는 세션 소유자로 제한됩니다. 로그인 및 사용자 이미지 흐름은 격리 Django 테스트로 확인했습니다. 상세 구성은 [아키텍처 문서](docs/ARCHITECTURE.md)를 참고하세요.

## 실행 방법

새 clone의 설정과 실제 Windows PowerShell/POSIX 명령은 [Local Setup Guide](docs/SETUP.md)에 있습니다. 최소 실행 순서는 다음과 같습니다.

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 로컬 전용 `DJANGO_SECRET_KEY`, SQLite, localhost origin을 설정한 뒤:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

별도 terminal에서:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm start
```

`.env.example`은 값이 들어 있는 `.env`를 생성하지 않습니다. 챗봇, YOLO, 외부 농업 API는 기본 설치·실행과 별도이며 Setup 문서의 선택 기능 안내를 확인하세요.

## 검증 결과

FC10 최종 검증은 2026-10-28에 로컬에서 재실행했습니다. 최종 문서 commit의 GitHub Actions #45에서도 Frontend·Backend·Browser E2E가 모두 성공했습니다.

| 검사 | 결과 | 검증 경계 |
| --- | --- | --- |
| Frontend Jest | 32 suites, 188 tests 통과 | UI·API 모듈 단위/컴포넌트 테스트 |
| Backend Django | 278개 중 277 통과, 1 skip | 기본은 mock 기반, 모델 opt-in 테스트는 기본 skip |
| Ruff lint·format, Django check, `pip check` | 통과 | 정적 검사 및 격리 테스트 DB |
| Playwright Chromium | 42개 중 40 통과, 2 skip | fixture 흐름 + 격리 Django session/CSRF/소유권; 실제 YOLO 아님 |
| axe 자동 검사 | 로그인·커뮤니티에서 자동 위반 0건 | 스크린리더 평가를 대체하지 않음 |
| 모바일 viewport | 320×640, 390×844 통과 | 브라우저 에뮬레이션, 실제 기기 아님 |
| GitHub Actions | [실행 내역](https://github.com/minjuko/farm-copilot/actions)에서 Frontend · Backend · Browser E2E 성공 확인 | 공개 CI |
| npm audit | 31건; production dependency 2건 | 세부 내용은 아래 알려진 한계 참고 |

Playwright fixture는 실제 서버 E2E가 아니며 실제 Django 검증은 전용 임시 SQLite·Media·Private Media를 사용합니다. 경계와 각 흐름은 [브라우저 E2E 문서](docs/FRONTEND_E2E.md)에 구분했습니다.

## 알려진 한계와 보안 위험

- **모델 성능:** YOLO 체크포인트의 실제 CPU 실행은 FC07에서 한 참고 이미지로 확인했지만 정확도·일반화 성능은 검증하지 않았습니다. ID 2와 4의 원천 라벨 관계도 미해결입니다. 자세한 내용은 [모델 현황](docs/DETECTION_MODEL.md)을 참고하세요.
- **공개 Git 이력:** 현재 tree는 체크포인트를 추적하지 않지만 과거 이력에 87,631,411 byte `best.pt` blob이 남아 있습니다. 공개 배포 허용 여부는 확인되지 않았습니다. 과거 `.env` 커밋에도 OpenAI 키 형식 및 SMTP·DB 자격 증명처럼 보이는 값이 있어 노출된 것으로 취급해야 합니다. 값은 문서에 싣지 않았고, 이력 재작성은 하지 않았습니다. 조치 경계는 [공개 저장소 감사](docs/FC10_PORTFOLIO_EVIDENCE.md#공개-저장소-위험)에 기록했습니다.
- **공급망:** 현재 npm audit은 전체 31건(낮음 9, 보통 6, 높음 16), production dependency 2건(보통)입니다. 다수는 CRA 5 toolchain의 전이 개발 의존성이고, production 2건은 React Router 6 계열입니다. 이번 문서 감사에서 강제 업그레이드는 하지 않았습니다.
- **미검증 운영 경계:** 실제 PostgreSQL·S3 bucket 정책·외부 농업 API·OpenAI·배포 환경, 실제 모바일 기기와 스크린리더는 검증하지 않았습니다.

## 상세 문서

| 문서 | 근거와 절차 |
| --- | --- |
| [Local Setup](docs/SETUP.md) | 로컬 실행, 환경변수, 선택 기능 및 최종 검증 |
| [Architecture](docs/ARCHITECTURE.md) | 라우트, 세션 인증, API 및 데이터 흐름 |
| [Detection model](docs/DETECTION_MODEL.md) | YOLO 계약, 매핑, 학습 provenance와 공개 이력 한계 |
| [AI detection operations](docs/AI_DETECTION_OPERATIONS.md) | artifact readiness, 비공개 이미지, 격리 테스트 |
| [Chatbot operations](docs/CHATBOT_OPERATIONS.md) | RAG readiness, 개인정보, 비용·장애 경계 |
| [Frontend E2E](docs/FRONTEND_E2E.md) | fixture/Django 테스트 구분, axe, 모바일 에뮬레이션 |
| [Portfolio evidence](docs/FC10_PORTFOLIO_EVIDENCE.md) | 팀 프로젝트와 개인 개선, FC01–FC10 검증 근거 |
