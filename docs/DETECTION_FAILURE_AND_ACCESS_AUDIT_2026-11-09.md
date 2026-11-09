# 병해충 탐지 예외 처리 및 사용자별 접근 권한 감사

작성일: 2026-11-09

## 범위와 결론

현재 저장소의 Django 탐지 앱과 React 진단 화면을 읽고, 기존 탐지 전용 백엔드·프론트 테스트를 실행했다. 테스트 데이터베이스와 임시 이미지 저장소, 프론트 mock을 사용했으며 운영 DB, 유료 API, 외부 서비스는 사용하지 않았다.

이번 감사에서 목록·상세·삭제·이미지 스트림의 사용자 소유권 우회나 검증한 실패 처리 결함은 재현되지 않았다. 기존 구현과 회귀 테스트가 요청 범위를 충족해 탐지 기능 코드는 수정하지 않았다. 이 문서와 연결 문서만 추가했다.

## 기존 구조와 호출 흐름

1. `frontend/src/components/templates/exam/DiagnosisTemplate.jsx`가 capability 상태를 확인하고 `detectFlow.js::validateDetectionFile`로 파일 존재, 크기, 확장자와 MIME을 확인한다. 선택한 파일은 로컬 object URL로 미리보기한다.
2. 진단 버튼은 `uploadInFlight` ref로 중복 제출을 막고 전역 로딩 상태를 켠 뒤 `frontend/src/apis/predict.js::uploadImage`를 호출한다. Axios 공통 클라이언트가 세션 쿠키와 CSRF 헤더를 처리한다.
3. `POST /detect/upload/`는 `backend/detect/urls.py`에서 `upload_image_for_detection`으로 연결된다. `login_required`가 비로그인 요청을 막고, CSRF middleware가 상태 변경 요청을 보호한다.
4. `backend/detect/views.py::validate_image_file`은 빈 파일, 10MiB 초과, 허용하지 않은 JPEG/PNG/WebP 형식, 파일 내용 불일치, 디코딩 오류와 20MP 초과 이미지를 검증한다. 업로드는 임시 파일로 복사되어 모델에 전달되고 `finally`에서 제거된다.
5. `process_image`는 `get_yolo_model`을 거친다. `detect/artifact.py::check_artifact_readiness`가 모델 파일 fingerprint, SHA-256, YOLO 클래스 계약과 CPU smoke inference를 검사한다. 모델 결과 중 신뢰도 0.6 이상인 최고 결과만 `PestModelClass`에 명시된 매핑으로 Pest에 연결한다. 무탐지 결과는 가짜 클래스로 대체하지 않는다.
6. 탐지 성공 시 사용자, 해충, 신뢰도, 결과 이미지가 `PestDetection`에 저장된다. DB 저장 예외는 트랜잭션으로 롤백하고 업로드된 이미지도 정리한다. 성공 응답은 기존 세션 필드와 세션 ID를 포함한다.
7. React는 응답을 `normalizeDetectionResult`로 확인한 후에만 `/info/<session_id>`로 이동한다. 실패는 사용자 안내 모달에 표시하고 `finally`가 중복 잠금과 로딩 상태를 해제한다. 파일을 다시 선택하거나 진단을 재시도할 수 있다.

주요 API는 다음과 같다.

| 메서드와 경로 | 동작 및 경계 |
| --- | --- |
| `POST /detect/upload/` | 로그인·CSRF 보호, multipart `image` 업로드 |
| `GET /detect/list_detection_sessions/` | `user=request.user` 조건으로 목록 제한 |
| `GET /detect/detection_session_details/<id>/` | 소유자 조건 조회, 다른 사용자/없는 ID에는 404 |
| `DELETE /detect/delete_detection_session/<id>/` | 소유자 조건 조회, DB 커밋 후 이미지 정리 |
| `GET /detect/detection_image/<id>/` | 소유자 조건 조회 후 이미지 스트리밍 |

상세·업로드 응답은 `serialize_detection`을 공유한다. `user_image_url`은 저장소 URL이 아니라 `/detect/detection_image/<id>/`이다. `PestDetection.image`는 `PestDetectionStorage`를 사용하고, 로컬 경로는 `DETECTION_IMAGE_ROOT`로 일반 `MEDIA_ROOT`와 겹치지 않도록 설정 검사한다. DEBUG의 `/media/` 정적 제공 경로와 S3의 기본 media 도메인에 탐지 저장물을 두지 않는 구조다. 이미지 endpoint는 `private, no-store` 및 `nosniff` 헤더를 설정한다. S3 ACL은 private 기본값을 요청하지만, 실제 bucket policy·CDN·proxy 구성은 이 로컬 검증 범위가 아니다.

## 예외 시나리오와 확인 결과

| 시나리오 | 구현 응답·저장 동작 | 확인 근거 |
| --- | --- | --- |
| 정상 업로드·추론 | 유효한 Pest 매핑이 있으면 200, 세션과 private 결과 이미지 저장 | `test_successful_upload_persists_private_image_and_returns_compatible_fields`; 추론 결과는 mock |
| 탐지 결과 없음/임계값 미달 | 400 `No pest was detected...`, 세션 미생성 | `test_no_detection_returns_400_without_creating_a_session`, 임계값 경계 테스트 |
| 미지원 형식·MIME 불일치·손상 이미지 | 400 validation JSON, 추론 임시파일 생성 전 종료 | `DetectionRuntimeTests`의 입력 검증 테스트 |
| 빈 파일 | 400 validation JSON | 입력 검증 테스트 |
| 10MiB 경계·초과 및 20MP 경계 | 경계 이하는 허용, 초과는 400; 초과 업로드에서 추론 임시파일 미생성 | 크기·픽셀 경계 테스트 |
| 모델 없음/로딩·무결성·런타임 실패 | capability는 제한 상태, 업로드는 일반 경로·내부 경로 비노출 503 | `test_missing_model_returns_controlled_503`, artifact readiness 테스트 |
| 추론·annotation·모델 출력 오류 | 503 등 제어된 서비스 오류; 임시 업로드는 제거 | `test_temp_image_is_removed_when_inference_fails`, annotation 및 model output 테스트 |
| DB 저장 실패 | 500 JSON, 트랜잭션 롤백, 생성된 파일 제거 | `test_database_failure_after_storage_save_removes_the_image`, `test_failed_session_save_cleans_up_the_generated_image` |
| 중복 제출·프론트 복구 | 진행 중 두 번째 클릭은 무시; `finally`에서 잠금/로딩 해제; 오류 메시지 표시 | `DiagnosisTemplate.test.jsx` 중복·실패 테스트. 명시적 재시도 버튼 대신 같은 파일로 다시 제출 가능 |

클라이언트의 MIME·확장자 검사는 사용자 편의용이고, 서버가 이미지 실제 형식과 디코딩을 다시 검증한다. `CustomExceptionMiddleware`가 API 예외를 JSON `{status, message, code, status_code}`로 변환한다. 정상 모델 가중치의 실시간 추론은 이 감사 실행에서 호출하지 않았다.

## 접근 권한 확인

기존 `DetectionSessionEndpointTests.test_only_the_authenticated_owner_can_stream_their_image`는 사용자 A가 만든 세션을 사용자 B로 전환하여 목록 제외, 상세 404, 삭제 404, 이미지 URL 404를 확인하고, A의 세션이 유지되는지 확인한다. 같은 테스트는 비로그인 이미지 요청의 401도 확인한다. 삭제 API는 허용되지 않은 B 요청으로 기록을 삭제하지 않는다.

`test_private_local_detection_image_is_not_served_from_media_url`는 일반 `/media/<path>` 접근이 404인지 확인한다. `test_image_response_contract_uses_an_authenticated_endpoint_not_storage_url`은 직렬화 중 `storage.url()`을 호출하지 않는지 확인한다. 레거시 로컬 이미지도 직접 media URL에서는 막되 소유자 endpoint로는 읽을 수 있는지 별도 테스트한다.

즉, API의 소유권 조건과 파일 자체의 공개 여부를 각각 점검했다. 응답에 들어가는 사용자 이미지 주소는 인증이 필요한 endpoint라 브라우저가 이미지 요청에도 같은 세션 쿠키와 credential CORS 정책을 사용한다. 공개 가능한 pest 참고 이미지는 별도 static/external URL이고 사용자 업로드 이미지와 구분된다.

## 테스트 환경 및 실행 결과

백엔드 의존성은 `backend/requirements.txt`, 개발 도구는 `requirements-dev.txt`, 선택적 AI 런타임은 `requirements-ai.txt`에 고정돼 있다. 탐지용 실제 YOLO는 크고 별도 artifact이며 `backend/detect/tests/test_live_model_integration.py`에서 `RUN_LIVE_DETECTION_INTEGRATION=1`로만 선택 실행한다. 이 테스트는 기본 자동 검증에서 skip되는 것이 의도된 구성이다.

2026-11-09 현재 체크아웃에서 실행한 결과:

- 통과: `backend/.venv/Scripts/python.exe manage.py test detect.tests.test_detection detect.tests.test_artifact_and_catalog --verbosity 2` — 59개 통과. Django test DB에서 전체 탐지 unit/endpoint 테스트 수행.
- 통과: `npm.cmd test -- --watchAll=false --runInBand --runTestsByPath src/components/templates/exam/DiagnosisTemplate.test.jsx src/components/templates/exam/detectFlow.test.js` — 2 suites, 34 tests 통과.
- 통과: `backend/.venv/Scripts/python.exe manage.py test` — 278개 중 277개 통과, 실제 모델 opt-in 테스트 1개 skip.
- 통과: `npm.cmd test -- --watchAll=false --runInBand` — 32 suites, 188 tests 통과.
- 통과: `npm.cmd run lint`, `npm.cmd run build` — ESLint 오류 없음, production build 성공.
- 통과: `backend/.venv/Scripts/ruff.exe check detect common`, `ruff format --check detect common` — 검사 통과, 32개 파일 포맷 확인.
- 실행하지 않음: 실제 체크포인트 추론 opt-in 테스트, S3/bucket 정책 및 배포 프록시 검증.

기본 탐지 테스트는 YOLO 추론을 mock/stub으로 분리하므로 checkpoint 자체의 품질이나 정확도는 검증하지 않는다. 저장소에는 로컬 `.env`, DB와 체크포인트가 존재하지만 본 검증은 테스트 runner의 격리 DB·임시 저장소·mock을 사용했고 이 자료를 출력하거나 변경하지 않았다. Git 기준 브랜치는 `main`, HEAD는 `d52adaa`이며 감사 시작 시 `docs/farm-copilot-audit.txt`와 PDF 2개가 미추적 상태였다. 이 기존 파일들은 수정하지 않았다.

## 변경 내역과 기여 범위

이번 작업에서 추가할 문서는 이 파일이다. 감사 과정에서는 재현된 코드 결함이 없어 Django·React 구현이나 테스트 코드를 변경하지 않았다.

팀 프로젝트 당시 역할은 저장소 `README.md`의 프로젝트 개요 및 담당 역할에 기록된 범위로 구분한다. 이번 문서의 실행 결과와 감사 판단은 프로젝트 종료 이후 이 세션에서 수행한 개인 검증으로, 당시 팀 산출물이나 팀 성과로 합산하지 않는다.

## 포트폴리오 문장

팀 프로젝트에서는 병해충 이미지 업로드와 진단 결과·이력 화면을 구현했다. 프로젝트 종료 후 현재 저장소의 예외 처리와 사용자별 접근 통제를 재감사하고 Django 테스트 59개와 React 테스트 34개로 업로드 실패·저장 정리·타 사용자 기록 및 이미지 차단을 확인했다. 이 검증에서 재현된 권한 우회나 처리 결함은 없어 코드 변경 없이 근거 문서를 추가했으며, 실제 모델 정확도와 배포 S3 정책은 이번 범위에서 검증하지 않았다.
