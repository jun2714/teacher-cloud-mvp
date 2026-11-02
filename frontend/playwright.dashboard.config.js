import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const python = process.env.DASHBOARD_PYTHON || fileURLToPath(new URL(
  process.platform === 'win32' ? '../backend/.venv/Scripts/python.exe' : '../backend/.venv/bin/python', import.meta.url))

export default defineConfig({
  testDir: './tests/dashboard',
  testMatch: /dashboard\.spec\.js/,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:8002', channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' },
  webServer: {
    command: `"${python}" tests/support/dashboard-server.py`,
    url: 'http://127.0.0.1:8002/admin/login/',
    reuseExistingServer: !process.env.CI,
  },
})
