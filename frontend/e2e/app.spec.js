const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

const authenticated = { is_authenticated: true, username: 'fixture-user', user_id: 5 };

async function mockApi(page, { auth = false, status = 200, detectionStatus = 200, failDetection = false } = {}) {
  await page.route('http://localhost:8000/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === '/login/auth_check/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(auth ? authenticated : { is_authenticated: false }) });
    if (path === '/api/capabilities/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ soil: { status: 'available', available: true }, prediction: { status: 'available', available: true }, detection: { status: 'available', available: true }, chatbot: { status: 'archived', available: false } }) });
    if (path === '/login/login/' && route.request().method() === 'POST') return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(status === 200 ? { status: 'success', username: 'fixture-user', user_id: 5, is_authenticated: true } : { message: '서비스를 일시적으로 사용할 수 없습니다.' }) });
    if (path === '/community/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ id: 41, title: '봄 감자 재배 질문', content: '씨감자 간격을 알려주세요.', user__username: '농부', creation_date: '2026-05-12T09:00:00Z', comment_count: 0 }]) });
    if (path === '/community/post/41/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 41, title: '봄 감자 재배 질문', post_type: 'sell', user_id: 5, username: '농부', creation_date: '2026-05-12T09:00:00Z', content: '씨감자 간격을 알려주세요.', comments: [] }) });
    if (path === '/selfchatbot/status/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'archived', message: '챗봇 기능을 사용할 수 없습니다.' }) });
    if (path === '/detect/list_detection_sessions/') {
      if (failDetection) return route.abort('failed');
      return route.fulfill({ status: detectionStatus, contentType: 'application/json', body: JSON.stringify(detectionStatus === 401 ? { error: 'Authentication required.' } : [{ session_id: 42, pest_name: '고추 탄저병', detection_date: '2026-05-12 10:00', confidence: 0.91, user_image_url: '/detect/detection_image/42/' }]) });
    }
    if (path === '/detect/detection_session_details/42/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ session_id: 42, pest_name: '고추 탄저병', confidence: 91.25, user_image_url: '/detect/detection_image/42/', detection_date: '2026-05-12 10:00', occurrence_environment: '고온 다습', symptom_description: '과실에 병반이 생깁니다.', prevention_methods: '환기를 유지합니다.', pesticide_name: '', db_image_url: null }) });
    if (path === '/detect/detection_image/42/') return route.fulfill({ status: 200, contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/pXcAAAAASUVORK5CYII=', 'base64'), headers: { 'Cache-Control': 'private, no-store' } });
    if (path === '/soil/get-crop-names/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ crop_names: ['감자'] }) });
    if (path === '/soil/address-search/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: [{ display_name: '강원도 춘천시 농장길 1', address_name: '강원도 춘천시 농장동 1', road_address_name: '강원도 춘천시 농장길 1', stdg_code: '4211010100', pnu_code: '4211010100100010000' }] }) });
    if (path === '/soil/soil_exam/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ crop_name: '감자', address: '강원도 춘천시 농장길 1', soil_data: [{ No: '1', Exam_Day: '20240101', PNU_Nm: '춘천시 농장 필지', ACID: '6.5', OM: '2.0', VLDPHA: '100', POSIFERT_K: '0.3', POSIFERT_CA: '5.0', POSIFERT_MG: '1.0', VLDSIA: '200', SELC: '1.2' }] }) });
    if (path === '/soil/get-soil-fertilizer-info/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: [{ pre_Fert_N: '10', pre_Fert_P: '5', pre_Fert_K: '8', post_Fert_N: '3', post_Fert_P: '0', post_Fert_K: '2', pre_Compost_Cattl: '500' }] }) });
    if (path === '/prediction/get_crop_names/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ crop_names: ['감자'] }) });
    if (path === '/prediction/get_region_names/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ region_names: ['강원도 춘천시'] }) });
    if (path === '/prediction/predict/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ session_id: 'fixture-session' }) });
    if (path === '/prediction/session_details/fixture-session/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ region: '강원도 춘천시', land_area: 100, total_income: 5200000, results: [{ crop_name: '감자', price: 1200, crop_ratio: 1, allocated_area: 100, adjusted_data: { '소득 (원)': 5200000, '총수입 (원)': 8000000, 총경영비: 2800000 }, crop_chart_data: [] }] }) });
    if (path === '/detect/upload/') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ session_id: 42, pest_name: '고추 탄저병', confidence: 91.25, user_image_url: '/detect/detection_image/42/', detection_date: '2026-05-12 10:00', occurrence_environment: '고온 다습', symptom_description: '과실에 병반이 생깁니다.', prevention_methods: '환기를 유지합니다.', pesticide_name: '', db_image_url: null }) });
    if (path.startsWith('/')) return route.fulfill({ status: status === 503 ? 503 : 200, contentType: 'application/json', body: JSON.stringify({ error: status === 503 ? '일시적으로 서비스를 사용할 수 없습니다.' : '[]' }) });
    return route.continue();
  });
}

test('비로그인 보호 경로는 로그인으로 이동', async ({ page }) => {
  await mockApi(page);
  await page.goto('/diagnosis-list');
  await expect(page.getByRole('heading', { name: '로그인' })).toBeVisible();
  await expect(page.getByLabel('이메일')).toBeVisible();
});

test('로그인 폼은 서버 오류를 안내한다', async ({ page }) => {
  await mockApi(page, { status: 503 });
  await page.goto('/login');
  await page.getByLabel('이메일').fill('user@example.test');
  await page.getByLabel('비밀번호').fill('Pass!23456');
  await page.locator('form').getByRole('button', { name: '로그인' }).click();
  await expect(page.getByRole('alert')).toContainText('서비스를 일시적으로 사용할 수 없습니다.');
  const dialog = page.getByRole('dialog', { name: '오류' });
  await expect(dialog).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(dialog.getByRole('button', { name: '확인' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(dialog).toBeHidden();
  await expect(page.locator('form').getByRole('button', { name: '로그인' })).toBeFocused();
});

test('키보드 탭으로 로그인 입력에 도달하고 포커스 표시를 확인한다', async ({ page }) => {
  await mockApi(page);
  await page.goto('/login');
  for (let attempt = 0; attempt < 10; attempt += 1) {
    if (await page.evaluate(() => document.activeElement?.id === 'email')) break;
    await page.keyboard.press('Tab');
  }
  const focusedEmail = page.locator('#email');
  await expect(focusedEmail).toBeFocused();
  const outline = await focusedEmail.evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(outline).not.toBe('none');
  await page.keyboard.press('Tab');
  await expect(page.locator('#password')).toBeFocused();
});

test('진단 이력은 인증된 fixture 이미지를 표시한다', async ({ page }) => {
  await mockApi(page, { auth: true });
  await page.goto('/diagnosis-list');
  await expect(page.getByText('고추 탄저병')).toBeVisible();
  await expect(page.getByAltText('고추 탄저병')).toBeVisible();
});

test('401 진단 이력 응답은 로그인 화면으로 되돌린다', async ({ page }) => {
  await mockApi(page, { auth: true, detectionStatus: 401 });
  await page.goto('/diagnosis-list');
  await expect(page.getByRole('heading', { name: '로그인' })).toBeVisible();
});

test('네트워크 실패는 진단 이력의 오류 상태로 표시한다', async ({ page }) => {
  await mockApi(page, { auth: true, failDetection: true });
  await page.goto('/diagnosis-list');
  await expect(page.getByRole('alert')).toContainText(/연결|불러오지|오류/);
});

test('커뮤니티 목록에서 게시글 상세로 이동한다', async ({ page }) => {
  await mockApi(page);
  await page.goto('/sell-board');
  await expect(page.getByRole('heading', { name: '판매 게시판' })).toBeVisible();
  await page.getByText('봄 감자 재배 질문').click();
  await expect(page.getByText('씨감자 간격을 알려주세요.')).toBeVisible();
});

test('수익 예측 입력을 fixture 응답 결과까지 완료한다', async ({ page }) => {
  await mockApi(page, { auth: true });
  await page.goto('/crop-test');
  await page.getByPlaceholder('재배 면적 (평)').fill('100');
  await page.getByPlaceholder('지역 선택').click();
  await page.getByText('강원도 춘천시', { exact: true }).click();
  await page.getByRole('combobox').fill('감자');
  await page.getByRole('option', { name: '감자' }).click();
  await page.getByPlaceholder('ex) 0.5, 1').fill('1');
  await page.getByRole('button', { name: /추가하기/ }).click();
  await page.getByRole('button', { name: '예측 결과 보러가기' }).click();
  await expect(page.getByText('예상 총수입', { exact: true })).toBeVisible();
});

test('토양 주소 검색, 필지 선택, 처방 fixture 흐름을 완료한다', async ({ page }) => {
  await mockApi(page, { auth: true });
  await page.goto('/soil');
  await page.getByLabel('작물 이름').fill('감자');
  await page.getByRole('option', { name: '감자' }).click();
  await page.locator('#soil-address').fill('강원도 춘천시 농장길 1');
  await page.getByRole('button', { name: '주소 검색' }).click();
  await page.getByRole('button', { name: /강원도 춘천시 농장길 1/ }).click();
  await page.locator('#soil-sample').selectOption('0');
  await expect(page.getByText('비료 처방량')).toBeVisible();
  await expect(page.getByText('10 (kg/10a)')).toBeVisible();
});

test('진단 파일 선택 후 fixture 진단 결과 화면을 연다', async ({ page }) => {
  await mockApi(page, { auth: true });
  await page.goto('/diagnosis');
  await page.locator('input[type="file"]').first().setInputFiles({ name: 'leaf.png', mimeType: 'image/png', buffer: Buffer.from('fixture image') });
  await page.getByRole('button', { name: '진단하기' }).click();
  await expect(page.getByText('고추 탄저병', { exact: true })).toBeVisible();
  await expect(page.getByAltText('사용자 진단 이미지')).toBeVisible();
});

test('비활성 챗봇 안내가 표시된다', async ({ page }) => {
  await mockApi(page, { auth: true });
  await page.goto('/chat/test-session');
  await expect(page.getByText('챗봇 기능이 현재 비활성화돼 있습니다.')).toBeVisible();
});

test('로그인 및 커뮤니티 화면은 axe 자동 검사에 위반이 없다', async ({ page }) => {
  await mockApi(page);
  await page.goto('/login');
  const login = await new AxeBuilder({ page }).analyze();
  expect(login.violations).toEqual([]);
  await page.goto('/board');
  const board = await new AxeBuilder({ page }).analyze();
  expect(board.violations).toEqual([]);
});

test('실제 격리 Django 세션은 로그인, CSRF, 사용자 이미지 소유권을 보장한다', async ({ page, request }) => {
  test.skip(test.info().project.name !== 'chromium', '실제 Django 경계는 데스크톱 Chromium에서 한 번 실행합니다.');
  await page.goto('/login');
  await page.getByLabel('이메일').fill('owner@example.test');
  await page.getByLabel('비밀번호').fill('E2ePass!234');
  await page.locator('form').getByRole('button', { name: '로그인' }).click();
  await expect(page.getByText('owner님')).toBeVisible({ timeout: 10000 });
  await page.goto('/diagnosis-list');
  await expect(page.getByText('테스트 해충')).toBeVisible();
  const ownerImage = page.locator('img[alt="테스트 해충"]').first();
  await expect(ownerImage).toBeVisible();
  await expect.poll(() => ownerImage.evaluate((image) => image.naturalWidth)).toBe(1);

  const cookies = await page.context().cookies('http://localhost:8000');
  const cookieHeader = cookies.map(({ name, value }) => `${name}=${value}`).join('; ');
  const csrf = cookies.find(({ name }) => name === 'csrftoken')?.value;
  expect(csrf).toBeTruthy();
  const own = await request.get('http://localhost:8000/detect/detection_image/1/', { headers: { Cookie: cookieHeader } });
  expect(own.status()).toBe(200);
  expect(own.headers()['cache-control']).toContain('no-store');
  expect(own.headers()['x-content-type-options']).toBe('nosniff');
  const anonymous = await request.get('http://localhost:8000/detect/detection_image/1/');
  expect(anonymous.status()).toBe(401);

  const otherContext = await page.context().browser().newContext();
  const otherPage = await otherContext.newPage();
  await otherPage.goto('/login');
  await otherPage.getByLabel('이메일').fill('other@example.test');
  await otherPage.getByLabel('비밀번호').fill('E2ePass!234');
  await otherPage.locator('form').getByRole('button', { name: '로그인' }).click();
  await expect(otherPage.getByText('other님')).toBeVisible({ timeout: 10000 });
  const otherCookies = await otherContext.cookies('http://localhost:8000');
  const otherHeader = otherCookies.map(({ name, value }) => `${name}=${value}`).join('; ');
  const forbidden = await request.get('http://localhost:8000/detect/detection_image/1/', { headers: { Cookie: otherHeader } });
  expect([403, 404]).toContain(forbidden.status());
  await otherContext.close();
});

test('모바일 viewport에서 주요 화면에 가로 넘침이 없다', async ({ page }) => {
  await mockApi(page);
  for (const path of ['/login', '/board']) {
    await page.goto(path);
    const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
    expect(dimensions.scroll, `${path} should fit the viewport`).toBeLessThanOrEqual(dimensions.client);
  }
});
