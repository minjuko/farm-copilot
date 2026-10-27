# 브라우저 E2E 및 접근성 검사

`frontend`의 `npm run test:e2e`는 Playwright Chromium에서 실행합니다. 데스크톱은 1280 × 800, 모바일 브라우저 에뮬레이션은 320 × 640 및 390 × 844 viewport를 사용합니다. 모바일 viewport 검증은 실제 단말기 검증을 대신하지 않습니다.

일반 시나리오는 Django API 요청을 Playwright route fixture로 대체합니다. 이 테스트는 React 화면과 알려진 JSON 응답 계약을 검증하며, 실제 API·YOLO 추론·외부 농업 API·OpenAI를 검증하는 E2E로 간주하지 않습니다.

별도 시나리오는 로컬 Django만 기동합니다. `config.e2e_settings`의 검사를 그대로 적용하며, 시스템 임시 디렉터리 아래 새 임시 root, SQLite, Media, Private Media를 만들고 테스트 전용 사용자를 생성합니다. Django 설정 검사, 스키마 migration, fixture 생성, runserver는 같은 프로세스에서 수행합니다. 서버 종료 시 marker와 디렉터리 이름을 확인한 경우에만 임시 root를 정리합니다. 이 흐름은 세션 로그인과 CSRF, 사용자별 진단 이력, 비로그인 이미지 요청, 타 사용자 이미지 접근 차단을 검사하며 YOLO 업로드 추론은 실행하지 않습니다.

axe-core는 로그인 및 커뮤니티 화면의 자동 접근성 규칙을 실행합니다. axe 결과는 WCAG 규칙에 대한 자동 검사이며, 스크린리더 사용성 평가를 대체하지 않습니다. 포커스 이동과 좁은 화면 가로 넘침은 별도 Playwright 검증을 둡니다.

Chromium 바이너리는 `npx playwright install chromium`으로 설치합니다. CI는 GitHub-hosted Ubuntu runner에 브라우저와 OS 의존성을 설치하며 브라우저 바이너리를 Repository에 보관하지 않습니다. 실패 시 screenshot, video, trace는 `frontend/test-results`에 저장됩니다.
