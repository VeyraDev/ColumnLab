import { expect, test } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const samplesDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../samples')

test('login register and reach workspace', async ({ page }) => {
  const user = `e2e_${Date.now()}`
  await page.goto('/login')
  await page.getByRole('button', { name: '没有账号？注册' }).click()
  await page.getByLabel('用户名').fill(user)
  await page.getByLabel('邮箱').fill(`${user}@example.com`)
  await page.getByLabel('密码').fill('secret12')
  await page.getByRole('button', { name: '注册' }).click()
  await expect(page).toHaveURL(/\/workspace/)
})

test('import demo_rle and show storage map', async ({ page }) => {
  const user = `e2e_import_${Date.now()}`
  await page.goto('/login')
  await page.getByRole('button', { name: '没有账号？注册' }).click()
  await page.getByLabel('用户名').fill(user)
  await page.getByLabel('邮箱').fill(`${user}@example.com`)
  await page.getByLabel('密码').fill('secret12')
  await page.getByRole('button', { name: '注册' }).click()
  await expect(page).toHaveURL(/\/workspace/)

  await page.goto('/imports')
  await page.locator('input[type="file"]').setInputFiles(path.join(samplesDir, 'demo_rle.csv'))
  await page.getByRole('button', { name: '开始导入' }).click()
  await expect(page).toHaveURL(/\/workspace\/\d+/, { timeout: 90_000 })
  await expect(page.getByText('列块存储映射')).toBeVisible({ timeout: 30_000 })
})
