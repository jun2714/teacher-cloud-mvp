import { defineConfig } from '@playwright/test'
import dashboard from './playwright.dashboard.config.js'

export default defineConfig({
  ...dashboard,
  testMatch: /guidance\.spec\.js/,
  webServer: [dashboard.webServer, {
    command: `"${process.execPath}" node_modules/vite/bin/vite.js --host 127.0.0.1 --port 6062`,
    url: 'http://127.0.0.1:6062/login',
    env: { VITE_API_PROXY: 'http://127.0.0.1:8002', VITE_API_BASE_URL: '/api' },
    reuseExistingServer: !process.env.CI,
  }],
})
