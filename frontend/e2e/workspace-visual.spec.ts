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

test.describe('Workspace visual regression', () => {
  test('1024×576 completed workspace', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 576 })
    await seedSession(page)
    await installWorkspaceMocks(page, 'completed')
    await gotoWorkspace(page)
    await runMockQuery(page)
    await page.screenshot({ path: screenshotPath('workspace-1024x576.png') })
    await page.screenshot({ path: screenshotPath('02-query-completed.png') })
  })

  test('1440×900 completed workspace', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await seedSession(page)
    await installWorkspaceMocks(page, 'completed')
    await gotoWorkspace(page)
    await runMockQuery(page)
    await page.screenshot({ path: screenshotPath('workspace-1440x900.png') })
  })

  test('01 idle state', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 576 })
    await seedSession(page)
    await installWorkspaceMocks(page, 'idle')
    await gotoWorkspace(page)
    await page.screenshot({ path: screenshotPath('01-idle.png') })
  })

  test('03 block active and skipped', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 576 })
    await seedSession(page)
    await installWorkspaceMocks(page, 'pruning')
    await gotoWorkspace(page)
    await runMockQuery(page)

    await page.locator('.storage-map-canvas .block-cell').first().click()
    await page.waitForTimeout(400)
    await page.screenshot({ path: screenshotPath('03-block-active-and-skipped.png') })
  })

  test('04 query failed', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 576 })
    await seedSession(page)
    await installWorkspaceMocks(page, 'failed')
    await gotoWorkspace(page)
    await page.getByRole('button', { name: '运行查询' }).click()
    await page.getByText('失败').waitFor({ state: 'visible', timeout: 15_000 })
    await page.screenshot({ path: screenshotPath('04-query-failed.png') })
  })
})
