import { test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import {
  gotoWorkspace,
  installWorkspaceMocks,
  runMockQuery,
  screenshotPath,
  seedSession,
} from './helpers/workspaceMocks'

const outDir = path.dirname(screenshotPath('placeholder.png'))

test.beforeAll(() => {
  fs.mkdirSync(outDir, { recursive: true })
})

const VIEWPORT = { width: 1918, height: 952 }

test.describe('Workspace visual regression · 1918×952', () => {
  test('idle', async ({ page }) => {
    await page.setViewportSize(VIEWPORT)
    await seedSession(page)
    await installWorkspaceMocks(page, 'idle')
    await gotoWorkspace(page)
    await page.screenshot({ path: screenshotPath('1918-idle.png') })
  })

  test('completed', async ({ page }) => {
    await page.setViewportSize(VIEWPORT)
    await seedSession(page)
    await installWorkspaceMocks(page, 'completed')
    await gotoWorkspace(page)
    await runMockQuery(page)
    await page.screenshot({ path: screenshotPath('1918-completed.png') })
  })

  test('active and skipped', async ({ page }) => {
    await page.setViewportSize(VIEWPORT)
    await seedSession(page)
    await installWorkspaceMocks(page, 'pruning')
    await gotoWorkspace(page)
    await runMockQuery(page)
    await page.locator('.storage-map-canvas .block-cell').first().click()
    await page.waitForTimeout(400)
    await page.screenshot({ path: screenshotPath('1918-active-skipped.png') })
  })

  test('inspector dictionary selected', async ({ page }) => {
    await page.setViewportSize(VIEWPORT)
    await seedSession(page)
    await installWorkspaceMocks(page, 'completed')
    await gotoWorkspace(page)
    await page.locator('.storage-map-canvas .block-cell').nth(2).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: screenshotPath('1918-inspector-dictionary.png') })
  })

  test('query failed', async ({ page }) => {
    await page.setViewportSize(VIEWPORT)
    await seedSession(page)
    await installWorkspaceMocks(page, 'failed')
    await gotoWorkspace(page)
    await page.getByRole('button', { name: '运行查询' }).click()
    await page.locator('.status-pane .status-label').filter({ hasText: '失败' }).waitFor({
      state: 'visible',
      timeout: 15_000,
    })
    await page.screenshot({ path: screenshotPath('1918-failed.png') })
  })
})
