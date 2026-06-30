<script setup lang="ts">
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import PageBackNav from '@/components/workspace/PageBackNav.vue'
import BenchmarkChart from '@/components/benchmark/BenchmarkChart.vue'
import BenchmarkCompareTable from '@/components/benchmark/BenchmarkCompareTable.vue'
import BenchmarkConclusion from '@/components/benchmark/BenchmarkConclusion.vue'
import BenchmarkConfigurator from '@/components/benchmark/BenchmarkConfigurator.vue'
import BenchmarkProgress from '@/components/benchmark/BenchmarkProgress.vue'
import { useBenchmarkStore } from '@/stores/benchmarkStore'
import type { MetricStats } from '@/api/benchmarks'

const store = useBenchmarkStore()
const {
  config,
  currentRun,
  events,
  loading,
  error,
  progress,
  encodedBytesRows,
  comparison,
  summaryMetrics,
  samples,
} = storeToRefs(store)

type StatKey = 'mean' | 'median' | 'p95'
type GroupKey = 'encoding' | 'column' | 'metric'

const statKey = ref<StatKey>('mean')
const groupBy = ref<GroupKey>('encoding')
const selectedMetric = ref('encoded_bytes')

const metricOptions = computed(() => {
  const keys = Object.keys(summaryMetrics.value)
  const suffixes = new Set<string>()
  for (const k of keys) {
    const parts = k.split('.')
    if (parts.length >= 2) suffixes.add(parts.slice(1).join('.'))
  }
  return Array.from(suffixes).sort()
})

const tableRows = computed(() => {
  return encodedBytesRows.value.map((row) => ({
    ...row,
    median: getStat(`${row.column}.${row.encoding}.encoded_bytes`, 'median'),
    p95: row.p95,
    mean: row.mean,
  }))
})

function getStat(key: string, stat: StatKey): number {
  const s = summaryMetrics.value[key] as MetricStats | undefined
  return s?.[stat] ?? 0
}

const chartBars = computed(() => {
  const metrics = summaryMetrics.value
  const entries: Array<{ column: string; encoding: string; metric: string; value: number }> = []

  for (const [key, stats] of Object.entries(metrics)) {
    const parts = key.split('.')
    if (parts.length < 2) continue
    const metric = parts.slice(1).join('.')
    if (selectedMetric.value && !metric.endsWith(selectedMetric.value) && metric !== selectedMetric.value) {
      if (!metric.includes(selectedMetric.value)) continue
    }
    entries.push({
      column: parts[0],
      encoding: parts[1] ?? '—',
      metric,
      value: (stats as MetricStats)[statKey.value] ?? 0,
    })
  }

  if (!entries.length) {
    return encodedBytesRows.value.map((row) => ({
      key: `${row.column}-${row.encoding}`,
      label: groupBy.value === 'column' ? row.column : row.encoding,
      value: row[statKey.value === 'p95' ? 'p95' : 'mean'] ?? row.mean,
      group: row.column,
    }))
  }

  const grouped = new Map<string, number>()
  for (const e of entries) {
    let label = e.encoding
    if (groupBy.value === 'column') label = e.column
    else if (groupBy.value === 'metric') label = e.metric
    const k = label
    grouped.set(k, (grouped.get(k) ?? 0) + e.value)
  }

  return Array.from(grouped.entries()).map(([label, value]) => ({
    key: label,
    label,
    value,
  }))
})

const chartTitle = computed(
  () => `${selectedMetric.value} (${statKey.value}) · 按${groupBy.value === 'encoding' ? '编码' : groupBy.value === 'column' ? '列' : '指标'}分组`,
)
</script>

<template>
  <div class="benchmark-workbench">
    <header class="workbench-header">
      <PageBackNav label="返回工作区" />
      <h1>性能基准实验台</h1>
    </header>

    <div class="workbench-body">
      <aside class="config-column">
        <BenchmarkConfigurator v-model:config="config">
          <button type="button" class="run-btn" :disabled="loading" @click="store.runBenchmark()">
            {{ loading ? '运行中…' : '运行实验' }}
          </button>
        </BenchmarkConfigurator>
      </aside>

      <main class="results-column">
        <div class="results-toolbar">
          <label>
            指标
            <select v-model="selectedMetric">
              <option v-for="m in metricOptions.length ? metricOptions : ['encoded_bytes', 'query.execute_ns']" :key="m" :value="m">
                {{ m }}
              </option>
            </select>
          </label>
          <label>
            统计量
            <select v-model="statKey">
              <option value="mean">均值</option>
              <option value="median">中位数</option>
              <option value="p95">P95</option>
            </select>
          </label>
          <label>
            分组
            <select v-model="groupBy">
              <option value="encoding">编码</option>
              <option value="column">列</option>
              <option value="metric">指标</option>
            </select>
          </label>
          <div class="toolbar-actions">
            <button type="button" :disabled="!currentRun" @click="store.downloadCsv()">导出 CSV</button>
            <button type="button" :disabled="!currentRun" @click="store.downloadJson()">导出 JSON</button>
          </div>
        </div>

        <BenchmarkProgress
          :events="events"
          :progress="progress"
          :status="currentRun?.status ?? null"
        />

        <p v-if="error" class="error">{{ error }}</p>

        <div v-if="currentRun?.status === 'completed'" class="results-body">
          <BenchmarkChart :bars="chartBars" :title="chartTitle" :y-label="statKey" />

          <div class="results-lower">
            <BenchmarkCompareTable :rows="tableRows" :stat-label="statKey" />
            <div class="side-panels">
              <BenchmarkConclusion :run="currentRun" :comparison="comparison" />
              <section v-if="samples.length" class="samples-panel">
                <h3>原始样本 ({{ samples.length }})</h3>
                <div class="samples-scroll mono">
                  <div v-for="(s, i) in samples.slice(0, 40)" :key="i" class="sample-line">
                    #{{ s.iteration }} {{ s.phase }} · {{ s.metric_name }} = {{ Math.round(s.value) }}
                  </div>
                </div>
              </section>
              <section v-if="currentRun.env" class="env-panel">
                <h3>运行环境</h3>
                <dl class="env-list">
                  <div v-if="currentRun.env.git_commit"><dt>commit</dt><dd class="mono">{{ currentRun.env.git_commit }}</dd></div>
                  <div v-if="currentRun.env.python"><dt>Python</dt><dd class="mono">{{ currentRun.env.python }}</dd></div>
                  <div v-if="currentRun.env.cpu_count"><dt>CPU</dt><dd class="mono">{{ currentRun.env.cpu_count }}</dd></div>
                </dl>
              </section>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.benchmark-workbench {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-app);
}

.workbench-header {
  flex-shrink: 0;
  padding: 10px 16px 0;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-panel);
}

.workbench-header h1 {
  margin: 4px 0 10px;
  font-size: 14px;
  font-weight: 600;
}

.workbench-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
}

.config-column {
  border-right: 1px solid var(--border-default);
  background: var(--bg-muted);
  padding: 12px;
  overflow: auto;
}

.run-btn {
  width: 100%;
  margin-top: 8px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid #374151;
  border-radius: var(--radius-control);
  background: #374151;
  color: #fff;
  cursor: pointer;
}

.run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.results-column {
  min-width: 0;
  min-height: 0;
  overflow: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.results-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  background: var(--bg-panel);
}

.results-toolbar label {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 10px;
  color: var(--text-tertiary);
}

.results-toolbar select {
  font-size: 12px;
  padding: 4px 8px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-app);
  min-width: 120px;
}

.toolbar-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
}

.toolbar-actions button {
  font-size: 11px;
  padding: 5px 10px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-muted);
  cursor: pointer;
}

.results-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.results-lower {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 10px;
  min-height: 0;
}

.side-panels {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.samples-panel,
.env-panel {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 8px 10px;
  background: var(--bg-panel);
}

.samples-panel h3,
.env-panel h3 {
  margin: 0 0 6px;
  font-size: 11px;
  font-weight: 600;
}

.samples-scroll {
  max-height: 120px;
  overflow: auto;
  font-size: 10px;
  color: var(--text-secondary);
}

.sample-line {
  padding: 1px 0;
}

.env-list {
  margin: 0;
  font-size: 10px;
}

.env-list div {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 4px;
  padding: 2px 0;
}

.env-list dt {
  color: var(--text-tertiary);
}

.env-list dd {
  margin: 0;
}

.error {
  color: var(--text-secondary);
  font-size: 12px;
}
</style>
