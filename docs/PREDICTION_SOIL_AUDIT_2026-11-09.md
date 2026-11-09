# 수익 예측·토양검정 기능 검증 — 2026-11-09

## 범위와 구분

이 문서는 저장소의 Django `prediction`·`soil` 앱과 React 화면을 기준으로 입력 검증, 외부 서비스 실패 처리, 결과 저장, 소유권 경계를 점검한 기록이다. 테스트는 Django 테스트 DB와 mock 응답을 사용했으며 운영 DB나 실제 외부 서비스에 연결하지 않았다.

README에 기록된 팀 프로젝트 당시 담당 범위는 공통 UI, 인증·커뮤니티, 수익 분석·토양검정 등 주요 화면과 API 연결이다. 이 문서의 코드 감사, 결함 재현, 후속 수정 및 회귀 검증은 프로젝트 종료 후 개인적으로 수행한 작업이며, 팀 당시 구현 성과와 구분한다.

## 기존 구조와 호출 흐름

### 수익 예측

- API는 `backend/prediction/urls.py`에 정의되어 있다. `POST /prediction/predict/`가 예측을 수행하고 `GET /prediction/list_sessions/`, `GET /prediction/session_details/<session_id>/`, `PATCH /prediction/update_session_name/<session_id>/`, `DELETE /prediction/delete_session/<session_id>/`가 이력을 관리한다. 작물·지역 선택지는 별도 GET API에서 제공한다.
- `CropPredictionPage.jsx`는 `predictionFlow.js`의 입력 검증을 거쳐 `predictCrops()`로 요청한다. 제출 중에는 재요청을 막고, 응답 오류를 사용자에게 표시하며 `finally` 경로에서 제출·전역 로딩 상태를 해제한다.
- `predict_income()`은 작물 비율과 재배 면적을 바탕으로 `crop_profitability_data.csv`의 기준 소득을 조정한다. 지역별 기상청 ASOS와 작물별 aT 가격 자료를 service 계층에서 요청하고, `services.py`의 응답을 병합해 요청 시점에 ElasticNet 모델을 학습·평가한 뒤 다음 가격을 계산한다. 별도 예측 모델 파일을 로드하는 구조는 아니다.
- `PredictionSession` 및 `PredictionResult` 저장은 외부 데이터 일부를 받은 뒤 `transaction.atomic()` 안에서 생성한다. 해당 블록 안의 가격 API·계산·저장 예외는 롤백 대상이다. 응답에는 `session_id`, `total_income`, 작물별 `results`, `r2_scores`가 포함된다.

### 토양검정·비료 처방

- API 경로는 `backend/soil/urls.py`에 정의되어 있다. 인증 사용자의 주소 검색(`GET address-search/`), 토양검정(`POST soil_exam/`), 비료 처방(`POST get-soil-fertilizer-info/`), 저장 이력 목록·상세·삭제(`GET crop_data/`, `GET crop_data/<session_id>/`, `DELETE delete_soil_data/<session_id>/`)가 있다. 작물 선택지는 공개 GET API다.
- `SoilTemplate`은 `useSoilAnalysis.js`를 통해 작물 선택 → 주소 검색 및 필지 선택 → 토양 정보 조회 → 비료 처방 요청의 흐름을 관리한다. 요청 중복 방지 ref와 로딩·오류 상태가 있고, 비료 처방 입력에는 선택 필지의 `PNU_Nm`을 사용한다.
- 백엔드는 Kakao 주소 API로 행정구역·필지 코드를 확인하고 농촌진흥청 토양검정 및 비료 처방 API를 호출한다. 토양검정 조회 자체는 DB에 쓰지 않는다. 비료 처방은 응답을 받은 뒤 UUID 기반 `session_id`로 추천 결과 행들을 트랜잭션 저장하며, 같은 계정의 여러 분석을 별도 이력으로 구분한다.

## 검증 범위와 기존 테스트

prediction·soil 서비스 테스트에는 저장소의 계약 fixture를 이용한 성공·빈 응답·오류 응답 파싱, API 키 누락, 잘못된 응답, 타임아웃, 필수 파라미터, API 응답 계약 테스트가 있다. 외부 HTTP 요청은 mock 처리한다. 프론트엔드 기존 테스트는 입력 helper, 토양 선택·결과·오류·재시도 및 상세 이력 UI를 다룬다.

확인한 입력·오류 계약은 다음과 같다.

- 예측 입력의 면적·작물 수·비율의 양수 및 합계 1 조건은 서버에서 검증한다. 기상·가격 외부 API의 연결·인증·쿼터/서버 오류와 타임아웃은 service 계층에서 제한된 `503`으로 변환하고, 데이터가 비어 있으면 `404` 계열로 처리한다.
- 토양 주소 입력은 정규화·길이 검사 후 서비스로 전달된다. 토양·비료 서비스는 API 키 누락, 타임아웃, HTTP/서비스 오류, 응답 형식 오류를 제어된 예외로 변환하고, 주소·토양 결과가 비어 있는 경우와 구분한다.
- 두 기능은 이미지 업로드를 사용하지 않는다. 사용자 이미지의 직접 URL 접근은 별도 병해충 탐지 감사 문서에서 검증한다.

## 재현된 문제와 수정

### 1. 예측 요청 형식 오류가 500으로 처리될 수 있음

`predict_income()`은 JSON을 파싱한 뒤 루트가 객체인지, 필수 필드가 있는지, 작물 이름이 문자열인지, 비율이 숫자 목록인지 검증하기 전에 `.get`, 키 접근, `float()` 변환을 수행했다. 선택 입력인 세션 ID·이름의 타입과 길이도 DB 제약에 맡겨져 있었다. 유효하지 않은 입력은 일반 예외 경로로 흘러 500이 되거나 지원하지 않는 작물·지역에서 외부 호출이 먼저 발생할 수 있었다.

`test_prediction_rejects_malformed_and_unsupported_inputs_before_external_calls`는 루트 배열, 필수값 누락, 잘못된 작물·비율·세션 필드 형식, 변환 불가 숫자, 미지원 작물·지역을 포함해 400 응답, 외부 호출 없음, 이력 미생성을 검증한다. 기존 코드의 키/숫자 변환 경로상 해당 값이 500으로 빠질 수 있음을 확인해 입력 검증을 추가했다. 서버는 필수 필드·타입·숫자 변환과 세션 필드 길이를 명시 검증하며, 지역 및 양쪽 기준 CSV에서 실제 지원하는 작물을 확인한 뒤 외부 서비스에 접근한다.

### 2. 다른 사용자의 예측 세션 이름 변경이 500을 반환함

목록·상세·삭제·이름 변경은 모두 요청 사용자를 조건으로 세션을 조회하고 있어 다른 사용자의 데이터를 반환하거나 변경·삭제하지는 않았다. 다만 `update_session_name()`은 소유자가 아닌 사용자의 요청에서 `PredictionSession.DoesNotExist`를 잡지 않아 실제로 HTTP 500이 반환됐다.

`PredictionSessionOwnershipTests.test_other_user_cannot_list_read_rename_or_delete_prediction_session`에서 사용자 A 세션을 사용자 B로 조회·수정·삭제해 재현했다. 테스트는 수정 전 rename 응답 500으로 실패했다. 누락된 예외 처리만 추가해 해당 요청도 404로 응답하게 했다. 목록은 B에게 빈 결과를 반환하고 상세·삭제·이름 변경은 404이며 A의 세션명과 DB 행은 유지된다.

`test_owner_can_rename_prediction_session`은 소유자 PATCH 성공과 DB 반영을 확인한다. 별도 mocked 정상 예측 요청 테스트는 HTTP 200 응답의 기존 필드와 세션·결과 저장을 확인하며, 외부 기상·가격 서비스와 계산기는 mock 처리한다.

### 3. 작물 변경 이후 이전 토양 조회 응답이 화면에 반영됨

토양 조회가 진행 중이어도 작물 입력은 바꿀 수 있었다. 이전 작물로 보낸 HTTP 요청이 작물 변경 후 도착하면 `changeCropName()`이 비운 토양 결과 상태를 낡은 응답이 다시 채워, 현재 선택 작물과 이전 작물의 토양 샘플이 함께 보일 수 있었다.

`SoilTemplate.test.jsx`의 지연 promise 테스트에서 pepper 조회를 보류한 뒤 tomato를 선택하고 이전 성공 응답 또는 실패 응답을 완료하도록 해 이 상태를 재현했다. 작물·주소 선택 변경 시 조회 버전을 올리고, 주소/토양 응답이 요청 당시 버전과 다르면 결과와 오류 상태 반영을 폐기하도록 수정했다. 회귀 테스트는 이전 성공 뒤 샘플 선택이 비활성화되고 비료 API가 호출되지 않는지, 이전 실패가 현재 화면에 오류를 띄우지 않는지 확인한다.

컴포넌트 unmount 시 조회 버전을 무효화하고 mount 상태를 내려, 이후 응답과 `finally`가 React 및 전역 로딩 상태를 갱신하지 않도록 했다. 지연 응답을 unmount 뒤 완료하는 테스트가 전역 로딩 setter 호출이 늘지 않는지 확인한다. 실행 중인 HTTP 요청 자체는 취소하지 않으므로 응답이 끝날 때까지 네트워크 작업은 지속될 수 있지만 완료 결과는 폐기된다.

## 접근 권한 검증

- 사용자 A/B를 분리한 prediction 테스트에서 B의 A 세션 목록·상세·이름 변경·삭제를 검증했다. 목록은 비어 있고 나머지는 404이며 DB의 세션명과 행은 보존된다.
- soil 목록은 `user_id=request.user.id`로 조회하며, 상세와 삭제도 `user_id`와 `session_id`를 함께 조건으로 사용한다. 테스트는 다른 사용자의 목록 제외·상세 404·삭제 비대상을 확인한다.
- 두 기능의 인증되지 않은 이력 요청은 공통 로그인 데코레이터에 의해 401로 거절되는지 확인한다.
- 예측과 토양 기능에는 이 감사 범위 내 업로드 이미지나 파일 URL이 없다. 따라서 이미지 URL 정책은 해당 기능에 적용되지 않으며, 병해충 이미지 접근은 `DETECTION_FAILURE_AND_ACCESS_AUDIT_2026-11-09.md`의 별도 결과를 참조한다.

## 저장 정합성 및 프론트엔드 상태

- 예측은 검증 및 기상 데이터 확보 후 저장 트랜잭션을 시작한다. 트랜잭션 안의 시장가격 조회·계산·결과 저장 실패 시 세션과 일부 결과가 함께 커밋되지 않는 구조다. 이 감사에서는 서비스 경계 mock을 사용했고, 별도 파일 저장은 없다.
- 토양검정 조회는 결과를 영구 저장하지 않는다. 비료 처방은 외부 응답을 받은 다음 DB 트랜잭션을 시작하므로 추천 행 저장 중 예외가 나면 일부 행만 남지 않는다. UUID 세션 ID는 같은 사용자의 독립 분석 간 충돌을 피하도록 생성한다.
- 예측 화면은 `isSubmitting` 및 `finally`로 중복 제출 방지와 로딩 복구를 처리한다. 토양 화면은 요청 중복 플래그 및 `finally`로 로딩을 정리하고, 서비스 오류·빈 결과를 각각 사용자 메시지로 표시한다. 이번 수정은 토양의 오래된 응답 경합만 보완했다.

## 테스트 및 검사 결과

2026-11-09 로컬 격리 환경에서 수행. 전체 결과에는 이번에 추가한 회귀 테스트가 포함된다.

| 검사 | 결과 | 범위 |
| --- | --- | --- |
| Django 전체 테스트 `python manage.py test --verbosity 1` | 285개 중 284개 통과, 1개 skip | 전체 앱, 격리 테스트 DB, 서비스 외부 호출은 mock/fixture |
| React 전체 `npm test -- --watchAll=false --runInBand` | 32 suites, 191 tests 통과 | UI·API·헬퍼 테스트 |
| React lint `npm run lint` | 통과 | `src` ESLint, warning도 실패 처리 |
| React production build `npm run build` | 통과 | CRA optimized build |
| Django `python manage.py check` | 통과 | 현재 설정의 시스템 검사 |
| Ruff `ruff check prediction soil` | 통과 | 수정 앱 정적 검사 |

prediction·soil 수정 테스트는 전체 Django 재실행에 포함했다. 전체 실행 중 오류 응답을 검사하는 mock 예외 로그가 있었지만 프로세스는 종료코드 0으로 완료됐다. 선택적 실모델 통합 테스트 1개는 skip됐으며 실물 추론 검증으로 간주하지 않는다.

## 검증 한계

- 외부 Kakao·기상청·aT·농촌진흥청 서비스의 실제 계정 키, 네트워크, 쿼터, 변경된 운영 응답을 확인하지 않았다. CI/로컬 mock 테스트 결과는 live API 가용성 보증이 아니다.
- 요청 시점에 학습하는 ElasticNet의 실제 운영 데이터 품질·예측 정확도를 평가하지 않았다.
- 배포 환경의 DB transaction isolation, proxy/auth 설정, 서비스 키 주입 및 실제 사용자 권한 배포 정책은 검증하지 않았다.
- 입력에 허용되는 지역·작물 기준은 저장소 CSV와 `REGION_CODES`에 한정해 확인했다. 데이터 자체의 최신성·농업적 타당성은 별도 검토 대상이다.
- Notion 포트폴리오 수정, 커밋 및 푸시는 수행하지 않았다.

## 변경 파일

- `backend/prediction/views.py` — 입력 형식/지원값 사전 검증 및 세션 소유권 없는 이름 변경 404 처리
- `backend/prediction/tests/test_runtime.py` — malformed 입력과 A/B 및 비인증 이력 접근 회귀 테스트
- `backend/soil/tests/test_soil.py` — 사용자별 목록 및 비인증 접근 테스트
- `frontend/src/components/templates/exam/useSoilAnalysis.js` — 오래된 토양 조회 응답 폐기
- `frontend/src/components/templates/exam/SoilTemplate.test.jsx` — 작물 변경 경합 회귀 테스트
- `docs/PREDICTION_SOIL_AUDIT_2026-11-09.md` — 본 감사 문서

## 면접·포트폴리오용 요약

프로젝트 종료 후 수익 예측의 잘못된 입력이 500으로 빠지고, 다른 사용자의 예측 세션 이름 변경이 500으로 노출되며, 토양 조회의 늦은 응답이 바뀐 작물 화면에 남는 문제를 회귀 테스트로 재현했습니다. 입력 검증과 소유권 오류 응답을 정리하고 오래된 비동기 응답을 폐기했으며, 최종 전체 백엔드·프론트엔드 테스트와 lint/build 결과로 수정 범위를 확인했습니다.
