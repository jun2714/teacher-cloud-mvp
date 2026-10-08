import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/browser',
  use: {
    baseURL: 'http://127.0.0.1:6061',
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
    launchOptions: { args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] },
  },
  webServer: {
    command: 'npm run dev -- --port 6061',
    url: 'http://127.0.0.1:6061',
    reuseExistingServer: !process.env.CI,
  },
})
