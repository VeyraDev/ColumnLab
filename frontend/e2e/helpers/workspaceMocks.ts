import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Page, Route } from '@playwright/test'

const e2eDir = path.dirname(fileURLToPath(import.meta.url))
const frontendDir = path.resolve(e2eDir, '..', '..')
const repoRoot = path.resolve(frontendDir, '..')

export const DEMO_DATASET_ID = 1
export const DEMO_TABLE_ID = 10

const storageMap = JSON.parse(
  fs.readFileSync(path.join(frontendDir, 'src/fixtures/storage-map.json'), 'utf8'),
) as {
  row_count: number
  columns: Array<{ name: string; logical_type: string; block_count: number }>
}

const blockPreview = JSON.parse(
  fs.readFileSync(path.join(frontendDir, 'src/fixtures/codec-selection.json'), 'utf8'),
)

export const LAYOUT_STORAGE = JSON.stringify({
  leftWidth: 196,
  rightWidth: 220,
  lowerHeightPx: 160,
  leftCollapsed: false,
  rightCollapsed: false,
  lowerCollapsed: false,
})

function apiOk(data: unknown) {
  return { code: 0, msg: 'ok', data }
}

function columnsFromMap() {
  return storageMap.columns.map((col, idx) => ({
    id: idx + 1,
    name: col.name,
    logical_type: col.logical_type.toUpperCase(),
    scale: 0,
    nullable: true,
    block_count: col.block_count,
    raw_bytes: 12000,
    encoded_bytes: 8000,
  }))
}

const physicalPlanTree = {
  type: 'Aggregate',
  label: 'Aggregate',
  details: { group_by: ['region'] },
  children: [
    {
      type: 'Project',
      label: 'Project',
      details: {},
      children: [
        {
          type: 'BitmapAnd',
          label: 'BitmapAnd',
          details: {},
          children: [
            {
              type: 'DictionaryFilter',
              label: 'DictionaryFilter',
              details: { column: 'category' },
              children: [
                {
                  type: 'RangeFilter',
                  label: 'RangeFilter',
                  details: { column: 'amount' },
                  children: [
                    {
                      type: 'BlockScan',
                      label: 'BlockScan',
                      details: { column: 'region' },
                      children: [],
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
  ],
}

const completedMetrics = {
  scanned_blocks: 14,
  pruned_blocks: 58,
  decoded_blocks: 2,
  bytes_read: 1_884_160,
  rows_examined: 8000,
  rows_output: 120,
  cache_hits: 1,
  compressed_operator_blocks: 2,
  peak_memory: 0,
  parse_time: 0.0012,
  optimize_time: 0.0034,
  execute_time: 0.0217,
  total_time: 0.0217,
  operators: [],
}

const pruningStates = [
  {
    column: 'region',
    block_id: 6,
    state: 'skipped',
    verdict: 'skip',
    reason: 'dictionary_filter',
  },
  {
    column: 'category',
    block_id: 4,
    state: 'scanned',
    verdict: 'read',
    reason: 'range_filter',
  },
  {
    column: 'amount',
    block_id: 2,
    state: 'to_read',
    verdict: 'pending',
    reason: 'pending_scan',
  },
]

export type QueryMockMode = 'idle' | 'completed' | 'failed' | 'pruning'

function buildExplain(mode: QueryMockMode) {
  if (mode === 'idle') return null
  if (mode === 'failed') {
    return {
      query_id: 42,
      status: 'failed',
      sql_text: "SELECT region FROM data WHERE category = '电子' AND amount > 1000 GROUP BY region",
      logical_plan: null,
      plan_tree: null,
      optimized_plan: null,
      optimized_plan_tree: null,
      physical_plan: null,
      physical_plan_tree: null,
      optimizer_trace: [],
      block_pruning: [],
      metrics: null,
      total_blocks: 72,
      pruned_blocks: 0,
      error: { code: 'SYNTAX', message: 'mock failure', line: 1, col: 1 },
    }
  }
  return {
    query_id: 42,
    status: 'completed',
    sql_text: "SELECT region FROM data WHERE category = '电子' AND amount > 1000 GROUP BY region",
    logical_plan: null,
    plan_tree: physicalPlanTree,
    optimized_plan: null,
    optimized_plan_tree: physicalPlanTree,
    physical_plan: null,
    physical_plan_tree: physicalPlanTree,
    optimizer_trace: [],
    block_pruning: mode === 'pruning' ? pruningStates : [],
    metrics: completedMetrics,
    total_blocks: 72,
    pruned_blocks: 58,
    error: null,
  }
}

export async function seedSession(page: Page) {
  await page.addInitScript(({ layout, token, user }) => {
    localStorage.setItem('columnlab_token', token)
    localStorage.setItem('columnlab_user', JSON.stringify(user))
    localStorage.setItem('columnlab.workspace.layout', layout)
  }, {
    layout: LAYOUT_STORAGE,
    token: 'visual-test-token',
    user: { id: 1, username: 'visual', email: 'visual@test.local' },
  })
}

export async function installWorkspaceMocks(page: Page, queryMode: QueryMockMode = 'idle') {
  let queryModeState = queryMode

  const dataset = {
    id: DEMO_DATASET_ID,
    name: 'sales_2026',
    description: 'visual fixture',
    source_file_name: 'demo.csv',
    source_sha256: 'abc',
    status: 'ready',
    active_version_id: 1,
    row_count: storageMap.row_count,
    table_count: 1,
    storage_path: '/data/columnlab/sales_2026',
  }

  const table = {
    id: DEMO_TABLE_ID,
    name: 'data',
    row_count: storageMap.row_count,
    row_group_count: storageMap.columns[0]?.block_count ?? 55,
  }

  const columns = columnsFromMap()

  async function fulfillJson(route: Route, data: unknown) {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(apiOk(data)),
    })
  }

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    const p = url.pathname

    if (p === '/api/datasets' && route.request().method() === 'GET') {
      return fulfillJson(route, [dataset])
    }
    if (p === `/api/datasets/${DEMO_DATASET_ID}`) {
      return fulfillJson(route, dataset)
    }
    if (p === `/api/datasets/${DEMO_DATASET_ID}/tables`) {
      return fulfillJson(route, [table])
    }
    if (p === `/api/tables/${DEMO_TABLE_ID}/columns`) {
      return fulfillJson(route, columns)
    }
    if (p === `/api/tables/${DEMO_TABLE_ID}/storage-map`) {
      return fulfillJson(route, storageMap)
    }
    if (p.match(/\/api\/columns\/\d+\/blocks\/\d+\/preview$/)) {
      return fulfillJson(route, blockPreview)
    }
    if (p === '/api/runtime') {
      return fulfillJson(route, {
        engine_version: '0.9.1',
        memory_used_bytes: 1_460_000_000,
        memory_total_bytes: 6_442_450_944,
        process_rss_bytes: 1_500_000_000,
      })
    }
    if (p === '/api/queries' && route.request().method() === 'GET') {
      const explain = buildExplain(queryModeState)
      return fulfillJson(route, explain
        ? [{
            id: 42,
            sql_text: explain.sql_text,
            status: explain.status,
            created_at: '2026-06-29T10:00:00Z',
          }]
        : [])
    }
    if (p === '/api/queries' && route.request().method() === 'POST') {
      if (queryModeState !== 'failed') queryModeState = 'completed'
      const explain = buildExplain(queryModeState)
      return fulfillJson(route, {
        query_id: 42,
        status: explain?.status ?? 'completed',
        error: explain?.error ?? null,
        plan_summary: explain?.status === 'failed' ? null : 'Aggregate → BlockScan',
        total_blocks: 72,
        pruned_blocks: explain?.status === 'failed' ? 0 : 58,
      })
    }
    if (p === '/api/queries/42/explain') {
      return fulfillJson(route, buildExplain(queryModeState))
    }
    if (p === '/api/queries/42/status') {
      const explain = buildExplain(queryModeState)
      return fulfillJson(route, {
        status: explain?.status ?? 'completed',
        metrics: explain?.metrics ?? null,
      })
    }
    if (p === '/api/queries/42/result') {
      return fulfillJson(route, {
        query_id: 42,
        status: 'completed',
        columns: ['region'],
        rows: [['华东'], ['华北']],
        total_rows: 2,
      })
    }
    if (p === '/api/auth/profile') {
      return fulfillJson(route, { id: 1, username: 'visual', email: 'visual@test.local' })
    }

    return fulfillJson(route, null)
  })
}

export async function gotoWorkspace(page: Page) {
  await page.goto(`/workspace/${DEMO_DATASET_ID}`)
  await page.getByText('列块存储映射').waitFor({ state: 'visible', timeout: 30_000 })
  await page.locator('.block-cell').first().waitFor({ state: 'visible', timeout: 30_000 })
  await page.waitForFunction(() => document.fonts.ready)
  await page.waitForTimeout(300)
}

export async function runMockQuery(page: Page) {
  await page.getByRole('button', { name: '运行查询' }).click()
  await page.locator('.status-pane .status-label').filter({ hasText: '已完成' }).waitFor({
    state: 'visible',
    timeout: 15_000,
  })
  await page.waitForTimeout(300)
}

export function screenshotPath(name: string) {
  return path.join(repoRoot, 'docs', 'screenshots', 'batch-1-1', name)
}
