# AI 기반 농업 지원 서비스 기여 증빙 감사

- 감사 기준일: 2026-10-14
- 감사 대상: 현재 `main` (`7de8fb0`)과 전체 Git 이력
- 원격 기본 브랜치: `origin/main`
- 대상자 식별 후보: Git 설정 `minjuko <rhalswn0526@gmail.com>`, 이력상 `고민주 <83636444+minjuko@users.noreply.github.com>`
- 판정 원칙: 작성자 정보는 탐색 단서일 뿐이다. 개인 기여 판정은 커밋 diff, 현재 코드, 테스트와 기존 문서가 함께 뒷받침할 때만 한다.

감사 시작 시 작업 트리는 `main...origin/main`으로 깨끗했다. 코드·기존 문서·테스트는 변경하거나 실행하지 않았고, 이 문서만 추가했다. `historical`과 `upstream`은 원본 팀 저장소를 가리키며 push가 비활성화되어 있다.

## 1. 프로젝트 및 개인 역할

농업코파일럿은 2024-06-17~2024-07-30에 6명이 만든 농업 지원 서비스다. 팀 전체 범위는 작물 수익 분석, YOLO 병해충 진단, 토양검정·비료 처방, RAG 챗봇, 커뮤니티와 회원 관리다. [현재 README](../README.md)와 [2024 원본 README](archive/README-2024-original.md)는 대상자의 당시 역할을 **프론트엔드 개발, 공통 UI와 주요 기능 연동**으로 설명한다.

확인 가능한 개인 역할은 다음과 같다.

- 2024년: React 초기 구성, MainLayout·TopBar·GNB, 커뮤니티 화면과 API 연동, 회원·인증·마이페이지 화면 및 일부 API 연동, 수익 예측·병해충·토양·챗봇의 프론트엔드 연동, 공통 로더와 오류 처리.
- 2024년의 제한적 백엔드 작업: 세션 인증, 사용자 관리 API, 프론트엔드가 소비할 JSON 계약 조정 등은 개별 diff가 있다. 다만 백엔드 전체 구현이나 AI 모델 구현을 개인 성과로 볼 수 없다.
- 2026년 개인 유지보수: 원본 프론트·백엔드 이력 통합, 실행환경 복원, 보안·외부 API 계약·오류 경계 보완, 프론트엔드 구조화, 회귀 테스트와 CI, 문서 정리.

커밋 수는 기여량의 품질 지표가 아니지만 이력 범위를 설명하는 참고값이다. 2024년 전체 이력에서 `minjuko` 256건과 `고민주` 3건, 2026년 현재 `main`에서 두 이름 합계 105건이 조회된다. 병합·백업·정리 커밋이 포함되며, 이메일이 다른 두 계정이 동일인이라는 최종 확인도 필요하므로 이 수치를 개인 성과로 인용해서는 안 된다.

## 2. 기능별 기여 근거

| 기능 | 현재 구현·API | 검증·상태 처리 | 관련 커밋과 개인 기여 판정 |
| --- | --- | --- | --- |
| 커뮤니티 | `frontend/src/components/templates/post/`, `frontend/src/components/molecules/PostDetail.jsx`, `frontend/src/apis/post.js`; 게시글·댓글 CRUD, 내 글·댓글 단 글 | `PostBoardPage`가 로딩 실패와 빈 목록을 구분하고 `useAsyncResource`를 사용한다. 작성·수정 폼 검증과 소유권 테스트가 있다. 백엔드는 `backend/community/`에서 서버 측 소유권을 재검증한다. | 2024 UI·CRUD: [`7927617`](https://github.com/minjuko/farm-copilot/commit/7927617), [`d97baa2`](https://github.com/minjuko/farm-copilot/commit/d97baa2), [`7b4235c`](https://github.com/minjuko/farm-copilot/commit/7b4235c), 타 사용자 버튼 수정 [`b1f492c`](https://github.com/minjuko/farm-copilot/commit/b1f492c). 2026 서버 소유권·계약: [`317183b`](https://github.com/minjuko/farm-copilot/commit/317183b), [`09aa1c5`](https://github.com/minjuko/farm-copilot/commit/09aa1c5). 개인 기여 강함. 단, 2024 백엔드 최초 게시판은 다른 팀원 이력도 존재한다. |
| 병해충 진단 | `DiagnosisTemplate`, `DiagnosisListTemplate`, `InfoTemplate`, `apis/predict.js`; multipart 업로드→Django `/detect/upload/`→결과 화면 | `detectFlow.js`가 MIME·확장자·빈 파일을 검증하고 400/503/미탐지를 구분한다. 결과 필드를 정규화하며 준비 중·제한·상태 조회 오류의 재확인을 제공한다. Mock UI/API 테스트와 백엔드 업로드·모델 계약 테스트가 있다. | 2024 프론트 연동 [`c0e4aef`](https://github.com/minjuko/farm-copilot/commit/c0e4aef), 화면 개선 [`282282e`](https://github.com/minjuko/farm-copilot/commit/282282e). 2026 오류 경계 [`193415c`](https://github.com/minjuko/farm-copilot/commit/193415c), 백엔드 추론 경계 [`b61c2a9`](https://github.com/minjuko/farm-copilot/commit/b61c2a9), 검증 [`c855aa2`](https://github.com/minjuko/farm-copilot/commit/c855aa2), [`89fa33d`](https://github.com/minjuko/farm-copilot/commit/89fa33d). **프론트 연동과 후속 안정화만 개인 기여로 표현 가능**. 모델 삽입은 팀원 `Leehanwoong`의 `deb17cc`; 학습 근거는 없다. |
| 작물 수익 예측 | `CropPredictionPage`, `CropSelectionPage`, `SessionDetails`, `apis/crop.js`; 예측 생성·이력·상세·이름 변경·삭제 | `predictionFlow.js`가 면적, 지역, 작물 수, 중복, 비율 양수·합계 1을 검증한다. 응답의 숫자·차트 배열을 정규화한다. 이력 로딩/빈 상태/실패/재시도 및 결과 정규화 테스트가 있다. | 2024 연동용 화면 [`ddedfe6`](https://github.com/minjuko/farm-copilot/commit/ddedfe6), JSON 계약 조정 [`7a28be9`](https://github.com/minjuko/farm-copilot/commit/7a28be9). 2026 흐름·테스트 [`129fad5`](https://github.com/minjuko/farm-copilot/commit/129fad5), 외부 시세 장애 격리 [`acb5bbc`](https://github.com/minjuko/farm-copilot/commit/acb5bbc), 계약 fixture [`16ed318`](https://github.com/minjuko/farm-copilot/commit/16ed318). 프론트 연동과 후속 안정화는 확인됨. 예측 모델 최초 구조·모델 코드는 여러 팀원 이력이므로 개인 모델 개발로 표현 불가. |
| 토양검정 | `SoilTemplate`, `SoilResults`, `SoilSampleSelect`, `useSoilAnalysis`, `apis/predict.js`; 주소 검색→토양 시료→필지 선택→비료 처방 | 주소·작물 필수값, 토양 항목 선택, 404 무처방, 외부 오류를 구분한다. `soilFlow.js`가 V2 필드를 프론트 계약으로 매핑한다. 컴포넌트와 서비스 Mock 테스트가 있다. | 2024 JSON/상세주소 연동 [`a9278e6`](https://github.com/minjuko/farm-copilot/commit/a9278e6), [`00681df`](https://github.com/minjuko/farm-copilot/commit/00681df). 2026 V2 전환·필드 수정 [`3a0a73c`](https://github.com/minjuko/farm-copilot/commit/3a0a73c), [`052841b`](https://github.com/minjuko/farm-copilot/commit/052841b), 프론트 흐름 [`105af3a`](https://github.com/minjuko/farm-copilot/commit/105af3a), fixture [`16ed318`](https://github.com/minjuko/farm-copilot/commit/16ed318). 프론트 연동 및 2026 외부 계약 보완은 확인됨. 팀의 토양 기능 전체를 개인 성과로 표현하면 안 된다. |
| 사용자 정보 관리 | `frontend/src/components/templates/user/`, `apis/user.js`, `AuthContext.js`, 라우트 가드; 가입·로그인·이름/비밀번호 변경·탈퇴·비밀번호 재설정 | `formValidation.js`와 각 폼이 형식·일치 여부를 검사한다. 서버 메시지와 fallback 오류를 표시하고 CSRF/세션 흐름을 사용한다. 폼·라우트·인증 API와 백엔드 인증 테스트가 있다. | 2024 세션 인증 [`206e11c`](https://github.com/minjuko/farm-copilot/commit/206e11c), 비밀번호·탈퇴 [`4d258b7`](https://github.com/minjuko/farm-copilot/commit/4d258b7), 정규식·예외처리 [`b981c42`](https://github.com/minjuko/farm-copilot/commit/b981c42). 2026 CSRF·재설정 강화 [`8512104`](https://github.com/minjuko/farm-copilot/commit/8512104), [`3177db0`](https://github.com/minjuko/farm-copilot/commit/3177db0). 개인 기여 강함. 최초 회원 백엔드에는 다른 팀원 기여가 있으므로 전체 소유 주장 금지. |
| 공통 로딩·오류·빈 상태 | `LoadingContext.js`, `GlobalLoader.jsx`, `hooks/useAsyncResource.js`, `apis/error.js` | 요청 카운터로 동시 요청을 추적하고 `finally`에서 종료한다. 비동기 hook은 최신 요청만 반영하고 unmount 후 갱신을 막으며 `refetch`를 제공한다. 5xx 내부 메시지는 안전한 fallback으로 바꾼다. 관련 단위 테스트가 있다. | 2024 글로벌 로더 [`3fb3f14`](https://github.com/minjuko/farm-copilot/commit/3fb3f14). 2026 동시 요청 카운터 [`588fb7b`](https://github.com/minjuko/farm-copilot/commit/588fb7b), 공통 hook [`3b7679b`](https://github.com/minjuko/farm-copilot/commit/3b7679b), 오류 기준 [`44eccb3`](https://github.com/minjuko/farm-copilot/commit/44eccb3). 개인 기여 강함. |

Git 작성자 외의 보강 근거는 2024 원본 README의 개인 역할 기술, 기능별로 이어지는 작은 커밋 연쇄, 2026년 해당 코드에 직접 추가된 테스트다. 그러나 공동 작업·병합 커밋은 단독 구현 증거에서 제외했다.

## 3. AI 모델·백엔드·프론트엔드 책임 구분

| 구분 | 저장소 근거 | 개인 기여 판정 |
| --- | --- | --- |
| A. AI 모델 직접 개발·학습 | YOLO checkpoint 삽입은 `Leehanwoong`의 `deb17cc`; 예측 모델 관련 최초 구조와 수정은 여러 팀원의 이력이다. 학습 노트북, 대상자 명의 학습 파이프라인, 데이터 전처리·학습 실험 또는 성능 개선 비교가 없다. | **확인 안 됨. 주장 금지.** |
| B. AI 모델 실행 백엔드 | `backend/detect/views.py`가 선택적 `ultralytics.YOLO` 로딩·추론·임계값·클래스 계약을 처리한다. `backend/prediction/`은 공공데이터와 예측 계산을 결합한다. | 2024 전체 실행부 소유는 확인 안 됨. 2026에는 모델 부재/계약 불일치/매핑 오류 경계와 테스트를 보강한 기여가 확인됨(`b61c2a9`, `2fbd844`, `3b4e7b8`). |
| C. 결과 전달 API | Django의 detect/prediction/soil/chatbot endpoint가 인증, 저장, 외부 호출과 JSON 응답을 담당한다. | 2024 일부 JSON 계약 조정은 확인되나 전체 API 구현은 팀 성과. 2026 외부 API V2 전환, 오류 격리와 계약 테스트는 개인 개선으로 확인됨. |
| D. 결과 사용 프론트엔드 | 이미지 업로드, 예측·토양 입력, 로딩/오류/빈 상태, 결과·이력 화면 | **핵심 개인 기여로 확인됨.** 다만 AI 알고리즘 개발이 아니라 AI/공공데이터 결과를 제품 UI로 연결한 경험이다. |
| E. 테스트·오류 처리 | 프론트 31개 테스트 파일, 백엔드 8개 테스트 모듈, Mock/fixture, CI | **2026 개인 기여로 강하게 확인됨.** 실제 모델·외부 서비스 end-to-end 검증과는 구분해야 한다. |

챗봇에는 LangChain·Chroma·OpenAI를 이용한 RAG 코드가 있으나 2024 최초 앱·뷰는 `suhwan` 등 팀원 이력이다. 대상자는 당시 채팅 목록·세션 UI와 API 분리를 했고, 2026에는 기능 제한·오류 처리를 보완했다. RAG 자체 개발을 개인 성과로 쓰는 것은 부적절하다.

## 4. 확인된 문제해결 사례

### 사례 1: 프론트·백엔드 API 응답 구조 불일치 조정 — 2024

1. **문제 상황**: 수익 예측과 토양 결과를 화면에서 사용할 때 JSON 구조가 맞지 않아 별도 테스트 화면과 계약 조정이 필요했다.
2. **원인**: 기능별 백엔드가 반환하는 키·중첩 구조와 React가 기대하는 구조가 개발 중 변경되었다.
3. **판단**: AI/외부 데이터 로직을 브라우저에서 직접 호출하지 않고 Django JSON 계약을 기준으로 화면 입력·결과를 맞췄다.
4. **수정**: 수익 예측 테스트 화면·요청/응답 처리(`ddedfe6`, `7a28be9`), 토양 JSON·상세주소 흐름(`a9278e6`, `00681df`)을 수정했다.
5. **검증 방법**: 커밋 diff의 실제 호출·렌더링 변경과 당시 API 테스트용 화면/로그 이력이 근거다.
6. **확인 결과**: 이후 기능 화면과 API 분리 커밋으로 흐름이 이어졌다. 성능·정확도 향상 수치는 확인되지 않았다.
7. **관련 파일/커밋**: `CropPredictionPage`, `SoilTemplate`, `apis/crop.js`, `apis/predict.js`; 위 네 커밋.

이 사례는 당시 문제해결 근거로 사용할 수 있으나, 일부 커밋에 백업 파일·로그와 다른 변경이 섞여 있어 “API 전체를 단독 설계했다”는 표현은 피한다.

### 사례 2: 여러 비동기 요청에서 로더가 먼저 사라지는 경쟁 상태 — 2026

1. **문제 상황**: boolean 전역 로딩은 동시에 두 요청이 실행될 때 먼저 끝난 요청이 `false`를 설정하여 아직 진행 중인 요청의 로더까지 숨길 수 있었다.
2. **원인**: 요청별 수명 대신 단일 boolean을 공유했다.
3. **판단**: 로딩을 요청 카운터로 바꾸고 각 요청이 정확히 한 번만 종료하도록 했다.
4. **수정**: `beginLoading()`이 종료 함수를 반환하고 중복 종료를 방지하며, `withLoading`은 `finally`에서 종료한다. 기존 호출을 위한 전환 API도 카운터를 사용한다.
5. **검증 방법**: `LoadingContext.test.js`에서 중첩 요청, 중복 종료, 오류 시 종료를 단위 테스트했다.
6. **확인 결과**: 코드상 `loadingCount > 0` 동안 로더가 유지되고 음수로 내려가지 않는다. 실제 사용자 체감 시간 개선 수치는 측정하지 않았다.
7. **관련 파일/커밋**: `frontend/src/LoadingContext.js`, `frontend/src/LoadingContext.test.js`, [`588fb7b`](https://github.com/minjuko/farm-copilot/commit/588fb7b).

### 사례 3: 실패한 이력 조회를 “빈 이력”으로 오인 — 2026

1. **문제 상황**: 수익 예측 이력 API 실패와 정상적인 빈 결과가 같은 화면으로 보이면 사용자는 데이터가 없는지 장애인지 판단하거나 재시도할 수 없다.
2. **원인**: 목록 상태가 데이터 유무만 보고 로딩 실패 상태를 별도로 보존하지 않았다.
3. **판단**: loading, error, empty, data를 상호 구분하고 실패 시 동일 loader를 다시 실행하는 명시적 재시도를 제공했다.
4. **수정**: `useAsyncResource`의 `error/refetch` 계약을 이용해 `CropSelectionPage`에 오류 안내와 `다시 시도` 버튼을 추가했다.
5. **검증 방법**: 첫 호출 reject→재시도 resolve 빈 배열을 순서대로 Mock한 컴포넌트 테스트를 추가했다.
6. **확인 결과**: 테스트에서 로딩 표시, 진짜 빈 이력, 실패 메시지, 재시도 후 정상 빈 상태가 각각 확인되었다. 실제 외부 서비스 복구율은 측정하지 않았다.
7. **관련 파일/커밋**: `CropSelectionPage.jsx`, `CropSelectionPage.test.jsx`, `useAsyncResource.js`, [`16ed318`](https://github.com/minjuko/farm-copilot/commit/16ed318).

### 보조 사례: 외부 시장가격 장애를 저장된 예측 상세와 격리 — 2026

`acb5bbc`는 상세 이력 조회 중 시장가격 재조회가 실패해도 저장된 예측 결과 전체를 500으로 만들지 않도록 외부 시세 실패를 빈 차트 데이터로 제한하고 41줄의 회귀 테스트를 추가했다. 이는 외부 API 실패 격리의 직접 증거다. 다만 빈 차트가 사용자에게 충분한 안내인지에 대한 UX 검증은 별개다.

## 5. 정량적 검증 근거

| 항목 | 확인된 값 | 해석과 한계 |
| --- | ---: | --- |
| 현재 프론트 테스트 파일 | 31 | 파일 개수이며 테스트 통과 수가 아니다. |
| 현재 백엔드 테스트 모듈 | 8 | `accounts`, `chatbot`, `common`, `community`, `detect`, `prediction`, `soil`에 분포한다. |
| 최신 문서화된 로컬 실행(2026-09-18) | 프론트 31 suites / 159 tests, 백엔드 130 tests | README 상단 기록. 이 감사에서는 재실행하지 않았다. 자동 테스트는 외부 API·운영 DB·S3·실제 YOLO/RAG를 호출하지 않았다. |
| 이전 문서화된 실행(2026-09-13) | 프론트 30 suites / 151 tests, 백엔드 117 tests | README 하단의 시점 고정 기록. 이후 `16ed318`, `89fa33d`가 테스트를 추가하여 최신 수치와 차이가 난다. 두 수치는 모순된 동일 실행 결과가 아니라 서로 다른 시점이다. |
| 정적 검색된 현재 백엔드 `test_*` 메서드 | 130 | 최신 README의 백엔드 수치와 일치하나 실행 성공 증거를 대신하지 않는다. |
| CI | `.github/workflows/ci.yml` | 프론트 `npm ci→lint→test→build`, 백엔드 의존성 설치→Ruff→Django check/test→pip check. 실제 Actions 실행 상태는 이번 감사에서 조회하지 않았다. |
| 외부 연동 수동 기록 | 토양 시료 1건, 날씨 365행, 시장가격 243행 | README 상단의 2026-09-18 기록. 단 한 번의 구조 확인이며 정확성·가용성·전체 지역 호환성 근거가 아니다. |

Mock/fixture는 응답 파싱, 오류 분기와 화면 상태를 검증한다. 실제 자격증명, `best.pt`, Chroma 인덱스, 운영 PostgreSQL·S3가 없는 CI이므로 실제 추론 품질, RAG 답변 품질, 외부 API end-to-end 성공 또는 배포 상태를 입증하지 않는다. 테스트 통과 수도 모델 성능 개선 수치로 바꿔 말할 수 없다.

## 6. 당시 구현과 이후 개선

| 시점 | 확인된 작업 | 표현 경계 |
| --- | --- | --- |
| 2024-06~07 팀 프로젝트 | 공통 UI·라우팅, 커뮤니티·회원 UI/API 연동, AI/공공데이터 기능 입력·결과·이력 화면, 글로벌 로더, 일부 JSON·세션 API 조정 | “팀 서비스에서 프론트엔드와 기능 연동을 담당”은 가능. AI 모델·백엔드 전체·팀 기능 전체를 단독 구현했다는 표현은 불가. |
| 2026-08~09 개인 유지보수 | 원본 FE/BE 이력 통합, 비밀값 외부화, 선택적 AI 의존성, 외부 API V2, 인증·소유권·오류 경계, 프론트 구조화, Mock/fixture 테스트, CI·문서 | “2026년에 개인적으로 재현성과 오류 처리를 보강”으로 별도 표기해야 한다. 이를 2024 대회 당시 성과로 소급하면 안 된다. |
| 2026-09-18 검증 | 로컬 테스트 기록, 제한적 실연동 구조 확인, 모델·RAG 부재 상태 검증 | 운영 배포나 실제 AI 정확도 검증으로 확대 금지. |

## 7. KT DS AI 활용 문항 적합성 평가

문항: “지원 직무와 관련하여 AI 기술을 활용해 문제를 해결하거나 의미 있는 성과를 만든 경험”

1. **AI 기능을 포함한 서비스 개발 경험 — 적합도 높음.** 병해충 진단·수익 예측 결과를 Django API를 통해 React 입력/결과/이력 화면으로 연결하고, 준비되지 않은 모델·매핑, 미탐지, 외부 데이터 실패를 사용자 상태로 분리한 근거가 있다. 가장 안전한 주제다.
2. **AI 도구를 직접 활용해 개발 문제를 해결한 경험 — 근거 없음.** 저장소의 `Copilot` 명칭은 서비스명·저장소명이며 GitHub Copilot 사용 기록이 아니다. ChatGPT·Claude·Gemini 등 생성형 AI 개발 도구 사용 기록도 찾지 못했다. 사용했다고 추정하면 안 된다.
3. **AI 모델 직접 개발·학습 경험 — 근거 없음.** 대상자 명의 학습 코드·실험·데이터·성능 비교가 없고 모델 삽입 이력은 다른 팀원에게 있다.

따라서 KT DS 문항에는 “AI 모델을 학습했다”가 아니라 **AI 기능을 실제 사용자 흐름에 통합하고, 불확실한 결과·모델 부재·외부 의존성 실패를 검증 가능한 상태와 테스트로 바꾼 경험**을 쓰는 것이 적합하다. 단, 대표적인 오류 경계·재시도 테스트는 2026 개인 개선임을 밝혀야 하며 2024 팀 프로젝트 당시 성과와 섞지 않는다.

## 8. 자기소개서·면접에 활용 가능한 사실

- “6인 팀에서 프론트엔드를 맡아 커뮤니티·회원 관리와 수익 예측·병해충·토양 기능의 입력, API 연동, 결과·이력 화면을 구현했다.”
- “모델을 직접 학습한 것이 아니라 백엔드가 제공한 AI 결과를 사용자가 이해하고 다시 행동할 수 있는 UI로 연결했다.”
- “2024년 개발 중 수익 예측·토양 API JSON 계약 변화에 맞춰 요청과 렌더링 구조를 조정했다.”
- “2026년 개인 유지보수에서 AI/외부 서비스가 없거나 실패한 경우를 성공처럼 보이지 않게 4xx/503, empty, error로 분리하고 재확인·재시도를 추가했다.”
- “동시 요청에서 boolean 로더가 먼저 꺼질 수 있는 문제를 요청 카운터로 바꾸고 중첩·오류 케이스를 단위 테스트했다.”
- “Mock과 비식별 fixture로 계약을 회귀 검증하되 실제 모델 추론·외부 API·운영 배포의 검증 범위와 명확히 구분했다.”

면접에서는 각 문장의 시점을 함께 말한다. 예: “팀 프로젝트 당시에는 연동 화면을 구현했고, 2026년 포트폴리오를 정리하며 실패 상태와 테스트를 개인적으로 보강했습니다.”

## 9. 미확인 사항과 표현 금지 항목

### 추가 확인 필요

- `minjuko` 이메일 계정과 `고민주` noreply 계정이 모두 본인인지 본인 확인이 필요하다.
- 공동 작업 당시 PR 리뷰, 업무 배정표, 회의록·Notion 원문은 로컬 저장소만으로 확인하지 못했다.
- 2024 커밋 중 `backup`, `merge`, `resolve`는 실질 기여 범위가 불명확하다.
- 최신 GitHub Actions의 실제 성공 여부, 운영 배포, 운영 PostgreSQL·S3 연동은 이번 로컬 감사 범위 밖이다.
- 최신 실자격증명 기반 외부 API, 실제 `best.pt` 추론, Chroma/OpenAI RAG 질의는 미검증이다.
- 2024 당시 테스트의 통과 건수와 브라우저/기기 범위는 확인되지 않았다.

### 표현 금지

- “YOLO/ElasticNet 모델을 직접 개발·학습·고도화했다.”
- “AI 정확도나 수익 예측 성능을 개선했다.” 성능 전후 비교 근거가 없다.
- “백엔드 또는 AI 기능 전체를 혼자 구현했다.”
- “생성형 AI 도구로 개발 문제를 해결했다.” 사용 기록이 없다.
- “159/130 테스트 통과로 서비스/모델 성능이 향상됐다.” 테스트 수는 회귀 검증 규모다.
- “실제 외부 서비스와 운영 배포까지 CI에서 검증했다.” CI는 Mock·SQLite 중심이다.
- “2026년 안정화 작업을 2024 팀 프로젝트 당시 수행했다.”
- 커밋 수를 코드 기여율이나 개인 성과 비율로 제시하는 표현.

## 10. 관련 파일·커밋 링크

### 핵심 파일

- 프론트 API: [`frontend/src/apis/`](../frontend/src/apis/)
- 커뮤니티: [`frontend/src/components/templates/post/`](../frontend/src/components/templates/post/), [`backend/community/`](../backend/community/)
- 병해충: [`frontend/src/components/templates/exam/DiagnosisTemplate.jsx`](../frontend/src/components/templates/exam/DiagnosisTemplate.jsx), [`frontend/src/components/templates/exam/detectFlow.js`](../frontend/src/components/templates/exam/detectFlow.js), [`backend/detect/views.py`](../backend/detect/views.py)
- 수익 예측: [`frontend/src/components/templates/crop/`](../frontend/src/components/templates/crop/), [`backend/prediction/`](../backend/prediction/)
- 토양검정: [`frontend/src/components/templates/exam/SoilTemplate.jsx`](../frontend/src/components/templates/exam/SoilTemplate.jsx), [`frontend/src/components/templates/exam/soilFlow.js`](../frontend/src/components/templates/exam/soilFlow.js), [`backend/soil/`](../backend/soil/)
- 사용자: [`frontend/src/components/templates/user/`](../frontend/src/components/templates/user/), [`backend/accounts/`](../backend/accounts/)
- 공통 상태: [`frontend/src/LoadingContext.js`](../frontend/src/LoadingContext.js), [`frontend/src/hooks/useAsyncResource.js`](../frontend/src/hooks/useAsyncResource.js), [`frontend/src/apis/error.js`](../frontend/src/apis/error.js)
- 품질: [CI workflow](../.github/workflows/ci.yml), [설치·실행 문서](SETUP.md), [현재 README](../README.md)

### 대표 커밋 묶음

- 2024 공통·커뮤니티·사용자: `5a44d11`, `70af7e7`, `7927617`, `d97baa2`, `7b4235c`, `206e11c`, `4d258b7`, `b981c42`, `3fb3f14`
- 2024 AI/외부 데이터 프론트 연동: `c0e4aef`, `ddedfe6`, `7a28be9`, `a9278e6`, `00681df`, `282282e`
- 2026 기능 안정화: `129fad5`, `105af3a`, `193415c`, `acb5bbc`, `052841b`, `b61c2a9`, `317183b`
- 2026 공통 구조·검증: `588fb7b`, `3b7679b`, `44eccb3`, `3593d22`, `16ed318`, `89fa33d`

커밋은 `https://github.com/minjuko/farm-copilot/commit/<해시>`에서 확인할 수 있다. 저장소 통합 전 경로와 현재 경로가 다를 수 있으므로, 2024 커밋은 해당 커밋 당시의 루트 `src/`, `detect/`, `prediction/`, `soil/` 경로를 기준으로 읽어야 한다.
