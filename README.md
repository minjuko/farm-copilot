# 농업코파일럿

> AI와 공공데이터를 연결해 수익 분석, 병해충 진단, 토양검정, 영농 상담을 제공하는 초보 농업인 지원 서비스

[![CI](https://github.com/minjuko/farm-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/minjuko/farm-copilot/actions/workflows/ci.yml)

KT AIVLE School 5기 Big Project에서 6명이 함께 만든 서비스입니다. 프로젝트 당시 서비스명은 **꾼꾼농사꾼**이며, **Collaboration상**을 수상했습니다.

저는 프론트엔드 개발자로 참여해 공통 UI와 인증·커뮤니티를 구현했으며, 백엔드·AI·공공데이터 기능을 사용자가 이용할 수 있는 화면 흐름으로 연결했습니다.

## 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 기간 | 2024.06.17–2024.07.30 |
| 인원 | 6명 — 프론트엔드 2 · 백엔드 2 · AI/Server 2 |
| 본인 역할 | 프론트엔드 — 공통 UI · 주요 기능 연동 |
| 성과 | KT AIVLE School 5기 Big Project Collaboration상 |
| 원본 저장소 | [프론트엔드](https://github.com/kt-bigproject28/kunkunnongsakun) · [백엔드](https://github.com/kt-bigproject28/bigproject28) |
| 상세 문서 | [농업코파일럿 상세 기술문서](https://app.notion.com/p/3d1622cea8638005938aca8f9f7d905c) |

## 주요 기능 및 화면

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
    <th>AI 병해충 진단</th>
  </tr>
  <tr>
    <td align="center"><img src="./docs/readme/03_soil_fertilizer.png" alt="토양검정 및 비료 처방 화면" width="320" /></td>
    <td align="center"><img src="./docs/readme/05_pest_detection.png" alt="AI 병해충 진단 결과 화면" width="320" /></td>
  </tr>
</table>

> 화면 이미지는 팀 프로젝트 최종 시연 자료를 바탕으로 구성했습니다.

### 주요 기능

| 기능 | 사용자 흐름 |
| --- | --- |
| 농작물 수익 분석 | 재배 조건 입력 → 예상 소득·시장가격 분석 → 차트 확인 |
| AI 병해충 진단 | 작물 이미지 업로드 → YOLO 분석 → 병해충 정보·진단 이력 확인 |
| 토양검정·비료 처방 | 농지 주소 입력 → 토양 시료 선택 → 작물별 처방 확인 |
| 농업 AI 챗봇 | 대화 세션 생성 → 질문 전송 → RAG 기반 답변·이력 확인 |
| 농업 커뮤니티 | 판매·구매 게시글과 댓글 작성·조회·수정·삭제 |
| 회원·마이페이지 | 회원가입·로그인, 회원정보·사용자 활동 관리 |

## 기술 스택

> 아래 기술은 프로젝트 전체 구성 기준입니다. 개인 구현 범위는 **본인 담당 및 기여** 섹션을 따릅니다.

| 영역 | 기술 |
| --- | --- |
| 프론트엔드 | React 18 · JavaScript · React Router · Axios · styled-components · Chart.js · Create React App |
| 백엔드 | Python · Django 5 · Django REST Framework |
| Database·Storage | PostgreSQL · AWS S3 |
| AI·Data | ElasticNet · YOLOv8 · PyTorch · pandas · NumPy · scikit-learn |
| RAG | LangChain · Chroma · OpenAI |
| External Data | Kakao 주소 검색 · aT 가격정보 · 기상청 ASOS · 농촌진흥청 토양검정·비료사용처방 V2 |

## 담당 역할 및 핵심 구현

- **공통 UI·인증:** 주요 내비게이션과 사용자 인증·마이페이지 흐름을 구현했습니다.
- **서비스 기능 연동:** 수익 분석 입력·결과, 병해충 이미지 업로드·진단 이력, 주소 기반 토양검정·비료 처방을 Django API와 연결했습니다.
- **커뮤니티·챗봇:** 게시글·댓글·페이지네이션과 챗봇의 대화·이력 화면을 구성했습니다.
- **API 구조·상태 관리:** 기능별 Axios API 모듈을 구분하고 입력·로딩·오류·빈 결과·재시도 상태를 일관되게 처리했습니다.

AI 모델과 백엔드 핵심 기능은 팀원과 역할을 분담했습니다. API 계약과 병해충 진단 응답 구조의 상세 내용은 [기술문서](https://app.notion.com/p/3d1622cea8638005938aca8f9f7d905c) 및 [모델 문서](docs/DETECTION_MODEL.md)에 정리했습니다.

## 트러블슈팅

### 기능별 API 응답 상태에 따른 화면 처리 일관성

- **문제:** 수익 분석·병해충 진단·토양검정은 요청 방식과 응답 형태가 달라 로딩 중·빈 결과·오류 상황을 화면마다 별도로 처리해야 했습니다.
- **원인:** 이미지 업로드, 단계별 조회, 분석 결과 요청의 데이터 흐름과 실패 조건이 서로 달랐습니다.
- **해결:** 기능별 API 모듈을 구분하고 입력 → 요청 → 로딩·오류·빈 결과 → 결과 흐름을 화면에서 일관되게 구성했습니다.
- **검증:** 프론트엔드 테스트와 CI로 주요 상태 처리를 검증했습니다. 외부 AI 모델 및 유료 API의 실연동 검증과는 구분합니다.

[상세 기술문서](https://app.notion.com/p/3d1622cea8638005938aca8f9f7d905c)

## 시작하기 (Getting Started)

### 백엔드

```bash
cd backend
python -m venv .venv
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 프론트엔드

```bash
cd frontend
npm ci
npm start
```

기본 백엔드 주소는 `http://127.0.0.1:8000`, 프론트엔드 주소는 `http://localhost:3000`입니다.

```dotenv
REACT_APP_API_BASE_URL=http://localhost:8000
```

환경변수·데이터베이스·외부 API·AI 모델 설정은 [Local Setup Guide](docs/SETUP.md)를 참고해 주세요.

## 테스트 및 코드 품질

아래는 2026-10-20 로컬 검증 결과입니다. CI 상태는 문서 상단의 GitHub Actions 배지를 확인해 주세요.

| 검증 항목 | 결과 |
| --- | ---: |
| 프론트엔드 Test Suites | **32 / 32 passed** |
| 프론트엔드 Tests | **185 / 185 passed** |
| 백엔드 Tests | **227 passed, 1 opt-in test skipped** |
| 실제 YOLO 통합 테스트 | **1 / 1 passed** (CPU · 격리 테스트 DB) |
| 실제 브라우저 AI 진단 E2E | **PASS** (격리 SQLite/Media · Chrome · 모바일 390px 확인) |
| 프론트엔드 ESLint | **passed** |
| 프론트엔드 Production Build | **passed** |
| Ruff (`detect`, `common`) | **passed** |
| 전체 Ruff | `data_preparation`의 기존 지적 3건 확인 |
| Backend `pip check` | **passed** |
| Django System Check | **0 issues** |

기본 backend 테스트는 mock 기반이며 실제 모델 통합 테스트는 별도 opt-in으로 실행했습니다. 브라우저 E2E는 전용 임시 DB/Media에서 로그인부터 실제 YOLO 진단과 이력 확인까지 검증했습니다. 외부 유료 API 호출은 포함되지 않습니다. 실행 범위와 재현 절차는 [AI detection operations](./docs/AI_DETECTION_OPERATIONS.md#격리된-실제-브라우저-e2e)을 참고하세요.

## 산출물 및 관련 문서

| 문서 | 내용 |
| --- | --- |
| [Local Setup Guide](./docs/SETUP.md) | Local 실행 · 환경변수 · Database · AI Artifact · 외부 API · Storage |
| [병해충 진단 모델 문서](./docs/DETECTION_MODEL.md) | 확인된 YOLO 계약 · AI Hub 출처 · 클래스 매핑 한계와 후속 작업 |
| [상세 기술문서](https://app.notion.com/p/3d1622cea8638005938aca8f9f7d905c) | 요구사항 · 설계 · 핵심 구현 · 문제 해결 · 개인 기여 |


