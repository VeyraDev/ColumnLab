import request from './request'

export interface BenchmarkConfig {
  kind: 'codec' | 'query'
  seed: number
  warmup_runs: number
  repeat_runs: number
  distribution: string
  row_count: number
  block_sizes?: number[]
  cache_mode: 'cold' | 'hot'
  pruning_enabled: boolean
  dataset_id?: number | null
  sql?: string | null
}

export interface MetricStats {
  count: number
  mean: number
  median: number
  p95: number
  stdev: number
  min: number
  max: number
}

export interface BenchmarkRun {
  id: number
  kind: string
  status: string
  config: BenchmarkConfig
  env: Record<string, unknown> | null
  summary: {
    kind?: string
    seed?: number
    distribution?: string
    row_count?: number
    metrics?: Record<string, MetricStats>
    comparison?: Record<string, number>
    env?: Record<string, unknown>
    config?: BenchmarkConfig
  } | null
  error_message: string | null
  created_at: string | null
  updated_at: string | null
}

export interface BenchmarkSample {
  iteration: number
  phase: string
  metric_name: string
  value: number
  extra_json: string
}

export interface BenchmarkEvent {
  run_id: number
  stage: string
  message: string
  progress: number
}

export async function submitBenchmark(config: Partial<BenchmarkConfig>): Promise<BenchmarkRun> {
  const { data } = await request.post<{ data: BenchmarkRun }>('/benchmarks', config)
  return data.data
}

export async function fetchBenchmark(runId: number): Promise<BenchmarkRun> {
  const { data } = await request.get<{ data: BenchmarkRun }>(`/benchmarks/${runId}`)
  return data.data
}

export async function fetchBenchmarkSamples(
  runId: number,
  offset = 0,
  limit = 500,
): Promise<{ total: number; items: BenchmarkSample[] }> {
  const { data } = await request.get<{ data: { total: number; items: BenchmarkSample[] } }>(
    `/benchmarks/${runId}/samples`,
    { params: { offset, limit } },
  )
  return data.data
}

export function benchmarkEventsUrl(runId: number): string {
  const token = localStorage.getItem('columnlab_token')
  const base = '/api/benchmarks'
  const qs = token ? `?token=${encodeURIComponent(token)}` : ''
  return `${base}/${runId}/events${qs}`
}

export async function exportBenchmarkCsv(runId: number): Promise<string> {
  const token = localStorage.getItem('columnlab_token')
  const resp = await fetch(`/api/benchmarks/${runId}/export.csv`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!resp.ok) throw new Error('导出 CSV 失败')
  return resp.text()
}

export async function exportBenchmarkJson(runId: number): Promise<string> {
  const token = localStorage.getItem('columnlab_token')
  const resp = await fetch(`/api/benchmarks/${runId}/export.json`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!resp.ok) throw new Error('导出 JSON 失败')
  return resp.text()
}
