import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  benchmarkEventsUrl,
  exportBenchmarkCsv,
  exportBenchmarkJson,
  fetchBenchmark,
  fetchBenchmarkProgress,
  fetchBenchmarkSamples,
  submitBenchmark,
  type BenchmarkConfig,
  type BenchmarkEvent,
  type BenchmarkRun,
  type BenchmarkSample,
  type MetricStats,
} from '@/api/benchmarks'

const DEFAULT_CONFIG: BenchmarkConfig = {
  kind: 'codec',
  seed: 42,
  warmup_runs: 1,
  repeat_runs: 3,
  distribution: 'run_length',
  row_count: 4096,
  cache_mode: 'cold',
  pruning_enabled: true,
}

export const useBenchmarkStore = defineStore('benchmark', () => {
  const config = ref<BenchmarkConfig>({ ...DEFAULT_CONFIG })
  const currentRun = ref<BenchmarkRun | null>(null)
  const samples = ref<BenchmarkSample[]>([])
  const events = ref<BenchmarkEvent[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const progress = ref(0)
  const eventSource = ref<EventSource | null>(null)

  const isRunning = computed(
    () => currentRun.value?.status === 'running' || currentRun.value?.status === 'pending',
  )
  const summaryMetrics = computed(() => currentRun.value?.summary?.metrics ?? {})
  const comparison = computed(() => currentRun.value?.summary?.comparison ?? {})

  const encodedBytesRows = computed(() => {
    const metrics = summaryMetrics.value
    const encodings = ['RAW', 'RLE', 'DICTIONARY'] as const
    const cols = ['qty', 'region']
    return cols.flatMap((col) =>
      encodings.map((enc) => {
        const key = `${col}.${enc}.encoded_bytes`
        const stats = metrics[key]
        return {
          column: col,
          encoding: enc,
          mean: stats?.mean ?? 0,
          p95: stats?.p95 ?? 0,
        }
      }),
    )
  })

  function reset() {
    events.value = []
    samples.value = []
    progress.value = 0
    error.value = null
    closeEvents()
  }

  function closeEvents() {
    eventSource.value?.close()
    eventSource.value = null
  }

  async function runBenchmark() {
    reset()
    loading.value = true
    try {
      const run = await submitBenchmark(config.value)
      currentRun.value = run
      subscribeEvents(run.id)
      await pollUntilDone(run.id)
      await loadSamples(run.id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '提交失败'
    } finally {
      loading.value = false
      closeEvents()
    }
  }

  function applyProgressEvent(payload: BenchmarkEvent) {
    events.value.push(payload)
    progress.value = payload.progress
  }

  function subscribeEvents(runId: number) {
    closeEvents()
    const es = new EventSource(benchmarkEventsUrl(runId))
    es.onmessage = (ev) => {
      try {
        applyProgressEvent(JSON.parse(ev.data) as BenchmarkEvent)
      } catch {
        /* ignore malformed */
      }
    }
    eventSource.value = es
  }

  async function syncProgress(runId: number) {
    try {
      const snap = await fetchBenchmarkProgress(runId)
      if (snap.progress > progress.value) {
        progress.value = snap.progress
      }
      if (snap.stage && snap.message) {
        const last = events.value[events.value.length - 1]
        if (!last || last.stage !== snap.stage || last.message !== snap.message) {
          applyProgressEvent({
            run_id: runId,
            stage: snap.stage,
            message: snap.message,
            progress: snap.progress,
          })
        }
      }
    } catch {
      /* polling fallback should not abort run */
    }
  }

  async function pollUntilDone(runId: number) {
    for (let i = 0; i < 600; i++) {
      await syncProgress(runId)
      const run = await fetchBenchmark(runId)
      currentRun.value = run
      if (['completed', 'failed', 'cancelled'].includes(run.status)) {
        if (run.status === 'failed') error.value = run.error_message ?? 'benchmark 失败'
        progress.value = run.status === 'completed' ? 1 : progress.value
        return
      }
      await new Promise((r) => setTimeout(r, 400))
    }
    error.value = '等待 benchmark 超时'
  }

  async function loadSamples(runId: number) {
    const data = await fetchBenchmarkSamples(runId, 0, 2000)
    samples.value = data.items
  }

  async function downloadCsv() {
    if (!currentRun.value) return
    const text = await exportBenchmarkCsv(currentRun.value.id)
    downloadBlob(text, `benchmark-${currentRun.value.id}.csv`, 'text/csv')
  }

  async function downloadJson() {
    if (!currentRun.value) return
    const text = await exportBenchmarkJson(currentRun.value.id)
    downloadBlob(text, `benchmark-${currentRun.value.id}.json`, 'application/json')
  }

  function downloadBlob(content: string, filename: string, mime: string) {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  function formatStats(stats: MetricStats | undefined): string {
    if (!stats) return '—'
    return `mean ${stats.mean.toFixed(1)} · p95 ${stats.p95.toFixed(1)} · σ ${stats.stdev.toFixed(1)}`
  }

  return {
    config,
    currentRun,
    samples,
    events,
    loading,
    error,
    progress,
    isRunning,
    summaryMetrics,
    comparison,
    encodedBytesRows,
    runBenchmark,
    downloadCsv,
    downloadJson,
    formatStats,
    reset,
  }
})
