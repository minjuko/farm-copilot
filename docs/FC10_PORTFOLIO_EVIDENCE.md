# 포트폴리오 근거 — 농업코파일럿

2026-10-28 최종 Repository와 테스트를 확인해 작성한 사실 중심 요약입니다. 자기소개서나 Notion에 옮길 초안이며 외부 자료를 대신하거나 실제 운영 검증을 주장하지 않습니다.

## 팀 프로젝트 소개

- **프로젝트명:** 꾼꾼농사꾼 (현재 검토 Repository: `minjuko/farm-copilot`)
- **기간·팀:** KT AIVLE School 5기 Big Project, 2024.06.17–2024.07.30, 6명
- **팀 구성:** 프론트엔드 2명, 백엔드 2명, AI/Server 2명으로 프로젝트 README에 기록
- **수상:** Collaboration상으로 프로젝트 README에 기록
- **목표:** 농업 초보자가 작물 수익 정보, 병해충 진단, 토양검정·비료 처방, 커뮤니티와 영농 상담 기능을 이용할 수 있는 웹 서비스
- **프로젝트 자료에 기록된 본인 역할:** 프론트엔드 담당. 공통 UI, 인증·마이페이지, 커뮤니티 화면과 주요 기능의 입력·결과 API 흐름을 구현한 것으로 기존 프로젝트 소개에 기록돼 있습니다.

팀원별 백엔드·AI 개발 기여는 이 문서에서 개인 실적으로 돌리지 않습니다. 본인 역할은 기존 프로젝트 자료의 담당 기록을 요약한 것이며, Git commit author만으로 역할을 역산하지 않았습니다.

## 팀 프로젝트에서 맡았던 구현

기존 React 소스에서 확인할 수 있는 화면과 코드 범위는 다음과 같습니다.

- React 기반 공통 레이아웃·탐색 및 사용자 화면
- 회원가입·로그인·세션 상태와 마이페이지 사용자 흐름
- 커뮤니티 목록·게시글·댓글·페이지 이동 화면
- 수익 분석, 병해충 진단, 토양검정 화면의 사용자 입력·결과 흐름을 Backend API에 연결
- 챗봇 대화·이력 화면 구성

이는 프론트엔드 화면과 API 소비자 흐름에 관한 내용입니다. Django service, DB schema, 모델 학습·가중치 생성, 외부 데이터 수집의 원 저작자나 팀 내 개인별 배정은 주장하지 않습니다.

## 2026년 개인 Repository 개선

2026년 개선은 당시 팀 서비스의 현재 실행·보안·검증 경계를 저장소에서 재현하고 기록하는 작업입니다. 원 모델을 재학습하거나 기존 팀 기능을 새로 구현했다고 주장하지 않습니다.

| 단계 | 문제와 접근 | Repository에서 확인한 결과 |
| --- | --- | --- |
| FC01–FC02 | Ruff와 Linux CI에서 드러난 코드·환경 불일치를 고치고 실제 GitHub Actions 결과를 확인 | Ruff lint/format 통과. Actions #34 Frontend·Backend 성공 |
| FC03 | 사용자 진단 이미지가 공개 URL로 노출될 가능성과 업로드 검증 경계를 조사 | private storage와 인증 이미지 endpoint, 사용자 소유권·업로드 제약 및 실패 cleanup 검증 |
| FC04 | 기존 npm 취약점과 CRA/직접 의존성 관계 조사 | 안전한 범위의 의존성 조정 후 audit 전체 결과 37에서 31로 감소. 현재 결과와 잔여 위험은 README에 기록 |
| FC05 | 운영 환경변수의 위험한 조합이 느슨한 기본값으로 실행될 가능성 조사 | production 설정을 fail-closed로 검사하고 조합별 설정 테스트 추가 |
| FC06 | 공공데이터와 Kakao 응답 오류·형식 변경이 API 오류나 잘못된 성공 데이터가 될 가능성 조사 | mock 기반의 파싱·필드·숫자·장애 처리 검증. 실제 Provider 호출은 하지 않음 |
| FC07 | YOLO runtime/체크포인트의 재현성 및 클래스 ID 근거 조사 | FC07 로컬에서 승인 artifact CPU smoke와 격리 업로드 통합 테스트 1건 실행. ID 2·4 중복 매핑과 학습 provenance는 미해결, 정확도 미검증 |
| FC08 | 챗봇의 실제 준비 상태, 사용자 질문 전송, 보존·비용 경계 확인 | 기본 비활성화, readiness/요청 검증과 mock 장애 테스트. 실제 OpenAI·임베딩 호출 없음 |
| FC09 | 반복 가능한 브라우저 테스트와 기본 접근성 자동화 부족 | fixture Playwright, 격리 Django session/CSRF/소유권 테스트, axe, 모바일 viewport 및 CI job 구성 |
| FC10 | README·검증 문서가 오래된 테스트 수를 표시하고 공개 Git 이력의 위험과 혼재 | 최종 HEAD 기준 문서 정합성 검사, 재현 가능한 검증 기록과 이력 위험을 별도 정리 |

## 검증된 결과와 경계

2026-10-28 기준 로컬 검증과 Actions #44에서 확인한 결과:

- Frontend Jest: **32 suites, 188 tests 통과**
- Backend Django: **278개 중 277 통과, 1 skip**
- Ruff lint·format, Django system check, pip check: 통과
- Frontend lint와 production build: 통과
- Playwright Chromium: **42개 중 40 통과, 2 skip**. Fixture 흐름과 실제 격리 Django 경계를 구분
- axe 자동 검사: 로그인·커뮤니티 화면에서 자동 위반 0건
- 320×640과 390×844 브라우저 viewport 검사 통과
- GitHub Actions #44: Frontend, Backend, Browser E2E 모두 성공

**Mock/fixture:** 프론트엔드 주요 입력·오류·결과 흐름과 API 응답 소비를 검사합니다. 실제 Django endpoint나 외부 API 검증으로 표현하지 않습니다.

**실제 Django 격리 E2E:** 테스트용 프로세스와 계정, 임시 SQLite·Media·Private Media를 사용합니다. 세션 로그인, CSRF, 이미지 본인 조회, 익명·타인 접근 차단과 응답 보안 헤더를 확인합니다. YOLO는 호출하지 않습니다.

**실제 YOLO:** FC07에서만 개발 PC 로컬 체크포인트를 사용한 CPU 사전검사와 업로드 통합 테스트를 실행했습니다. 참조 이미지 한 장의 추론 가능성은 성능·정확도 검증이 아닙니다. 공개 CI는 체크포인트 없이 실행합니다.

**axe·모바일:** axe는 선택된 로그인·커뮤니티 화면을 자동 검사한 결과입니다. 스크린리더 실제 사용성 평가가 아니며 viewport는 브라우저 에뮬레이션으로, 실제 모바일 단말이 아닙니다.

실제 aT·기상청·Kakao·농촌진흥청 API, OpenAI/임베딩, AWS S3, PostgreSQL, 운영 배포는 호출·접속하지 않았습니다. npm audit은 현재 31건이며 production dependency 2건이 남아 있습니다.

## 공개 저장소 위험

최종 현재 tree에서 `.env`, 모델 파일, 사용자 업로드 media와 Chroma 인덱스는 추적되지 않고 ignore 대상입니다. 하지만 공개 Git 이력은 별개입니다.

- 2024년 commit `deb17cc`의 `best.pt` blob은 87,631,411 bytes입니다. FC07 로컬 체크포인트와 hash가 일치합니다. 체크포인트 공개·재배포 허가는 확인되지 않았습니다.
- 과거 commit의 `.env`에는 실제 키로 보이는 OpenAI key 형식과 SMTP·DB credential field 값이 포함됐습니다. 값 자체는 기록하지 않았고 현재 유효 여부를 공급자에 확인하지 않았습니다. 이미 노출된 것으로 취급하고, 사용 중일 수 있는 credential은 소유자가 폐기·교체해야 합니다.
- 새 commit에서 파일을 지워도 기존 blob은 사라지지 않습니다. 공개 이력 정리는 history rewrite와 force update가 필요하고, fork·clone·기존 사본을 원격으로 회수할 수 없습니다. FC10은 사용자 지시대로 이력 재작성, credential 변경, Repository 공개 범위 변경을 하지 않았습니다.

이 위험은 기능 테스트 성공과 별개입니다. 모델 배포 권리 확인과 과거 credential의 회전 상태 확인이 남아 있어 공개 이력 정리는 별도 승인·협업 과제로 두어야 합니다.

## 포트폴리오에 사용할 수 있는 요약 초안

> 6명 규모의 농업 지원 서비스 팀 프로젝트에서 프론트엔드 개발을 맡아 공통 UI와 사용자 인증·커뮤니티, 주요 분석 기능의 입력부터 결과까지 화면 흐름을 구현했습니다. 이후 개인 Repository 개선에서는 세션 인증 이미지 접근, 운영 환경설정 검증, 외부 API 오류 경계, YOLO 실행 계약과 챗봇 readiness를 점검하고 Jest·Django·Playwright 기반 검증을 보강했습니다. fixture 기반 화면 테스트와 실제 격리 Django 테스트, 로컬 opt-in YOLO 실행을 별도 경계로 유지했으며, CI에서 Frontend·Backend·Browser E2E가 통과하는 것을 확인했습니다. 모델 정확도와 실제 운영 Provider·배포 동작은 검증 범위에 포함하지 않았습니다.

사용 전 본인 담당 기능과 수상·팀 구성은 본인이 보관한 당시 배정 자료와 프로젝트 공식 기록으로 다시 대조하세요.
