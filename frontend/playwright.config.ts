import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)))
const repoRoot = path.resolve(frontendDir, '..')

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: path.join(repoRoot, 'backend'),
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: 'npm run preview -- --host 127.0.0.1 --port 4173',
      cwd: frontendDir,
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
})
