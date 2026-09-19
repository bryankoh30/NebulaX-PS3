import { defineConfig, devices } from '@playwright/test';
const port = process.env.PLAYWRIGHT_PORT ?? '5174';
export default defineConfig({
  testDir: './tests', timeout: 30000, fullyParallel: true,
  use: { baseURL: `http://127.0.0.1:${port}`, trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } },
  ],
  webServer: { command: `npm run dev -- --host 127.0.0.1 --port ${port} --strictPort`, url: `http://127.0.0.1:${port}`, reuseExistingServer: false,
    env: { VITE_USE_MOCK_API: 'false', VITE_ENABLE_REVIEWS: '', VITE_ENABLE_ZIP_EXPORT: '' } },
});
