const { defineConfig, devices } = require('@playwright/test');

const isCI = Boolean(process.env.CI);

module.exports = defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  workers: isCI ? 2 : undefined,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  outputDir: 'test-results',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } } },
    { name: 'mobile-320', use: { browserName: 'chromium', isMobile: true, hasTouch: true, deviceScaleFactor: 2, viewport: { width: 320, height: 640 } } },
    { name: 'mobile-390', use: { browserName: 'chromium', isMobile: true, hasTouch: true, deviceScaleFactor: 2, viewport: { width: 390, height: 844 } } },
  ],
  webServer: [
    {
      command: 'npm start',
      cwd: __dirname,
      url: 'http://localhost:3000',
      reuseExistingServer: !isCI,
      timeout: 120000,
      env: { BROWSER: 'none', HOST: '0.0.0.0', PORT: '3000', REACT_APP_API_BASE_URL: 'http://localhost:8000' },
    },
    {
      command: 'node e2e/start-django.mjs',
      cwd: __dirname,
      url: 'http://localhost:8000/login/auth_check/',
      reuseExistingServer: false,
      timeout: 120000,
      env: { E2E_DJANGO: '1' },
    },
  ],
});
