<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import PageBackNav from '@/components/workspace/PageBackNav.vue'
import BenchmarkChart from '@/components/benchmark/BenchmarkChart.vue'
import BenchmarkCompareTable from '@/components/benchmark/BenchmarkCompareTable.vue'
import BenchmarkConclusion from '@/components/benchmark/BenchmarkConclusion.vue'
import BenchmarkConfigurator from '@/components/benchmark/BenchmarkConfigurator.vue'
import BenchmarkProgress from '@/components/benchmark/BenchmarkProgress.vue'
import { useBenchmarkStore } from '@/stores/benchmarkStore'
import type { MetricStats } from '@/api/benchmarks'
import {
  buildEncodingCompareRows,
  metricTitle,
  resolveAnalysisColumn,
} from '@/utils/benchmarkAnalysis'
import {
  benchmarkMetricLabel,
  distributionLabels,
  isStorageBenchmarkMetric,
  isTimingBenchmarkMetric,
} from '@/utils/terminology'

const store = useBenchmarkStore()
const {
  config,
  currentRun,
  events,
  loading,
  error,
  progress,
  summaryMetrics,
  samples,
} = storeToRefs(store)

type GroupKey = 'encoding' | 'column'
type StatKey = 'median' | 'p95'

const analysisColumn = ref('qty')
const groupBy = ref<GroupKey>('encoding')
const selectedMetric = ref('encoded_bytes')
const statKey = ref<StatKey>('median')

watch(
  () => config.value.distribution,
  () => {
    analysisColumn.value = resolveAnalysisColumn(config.value)
  },
  { immediate: true },
)

const isCodecRun = computed(() => (currentRun.value?.kind ?? config.value.kind) === 'codec')

const metricOptions = computed(() => {
  const keys = Object.keys(summaryMetrics.value)
  const suffixes = new Set<string>()
  for (const k of keys) {
    const parts = k.split('.')
    if (parts.length >= 2) suffixes.add(parts.slice(1).join('.'))
  }
  return Array.from(suffixes).sort()
})

const storageMode = computed(() => isStorageBenchmarkMetric(selectedMetric.value))

const encodingCompareRows = computed(() =>
  buildEncodingCompareRows(summaryMetrics.value, analysisColumn.value),
)

const chartBars = computed(() => {
  if (isCodecRun.value && storageMode.value && groupBy.value === 'encoding') {
    return encodingCompareRows.value.map((row) => ({
      key: row.encoding,
      label: row.encoding,
      value: row.relativePercent,
      relativePercent: row.relativePercent,
      absoluteBytes: row.encodedBytes,
    }))
  }

  const metrics = summaryMetrics.value
  const encodings = ['RAW', 'RLE', 'DICTIONARY']
  if (groupBy.value === 'encoding') {
    return encodings
      .map((enc) => {
        const key = `${analysisColumn.value}.${enc}.${selectedMetric.value}`
        const stats = metrics[key] as MetricStats | undefined
        if (!stats) return null
        const value = stats[statKey.value] ?? stats.mean
        return { key: enc, label: enc, value }
      })
      .filter(Boolean) as Array<{ key: string; label: string; value: number }>
  }

  const cols = ['qty', 'region']
  const fixedEnc = 'RAW'
  return cols
    .map((col) => {
      const key = `${col}.${fixedEnc}.${selectedMetric.value}`
      const stats = metrics[key] as MetricStats | undefined
      if (!stats) return null
      return { key: col, label: col, value: stats[statKey.value] ?? stats.mean }
    })
    .filter(Boolean) as Array<{ key: string; label: string; value: number }>
})

const timingRows = computed(() => {
  const metrics = summaryMetrics.value
  const encodings = ['RAW', 'RLE', 'DICTIONARY']
  return encodings
    .map((enc) => {
      const key = `${analysisColumn.value}.${enc}.${selectedMetric.value}`
      const stats = metrics[key] as MetricStats | undefined
      if (!stats) return null
      return {
        encoding: enc,
        median: stats.median,
        p95: stats.p95,
        stdev: stats.stdev,
      }
    })
    .filter(Boolean) as Array<{ encoding: string; median: number; p95: number; stdev: number }>
})

const chartTitle = computed(() => {
  if (isCodecRun.value && storageMode.value) {
    return `${analysisColumn.value} 列不同编码的存储开销`
  }
  return metricTitle(selectedMetric.value, groupBy.value)
})

const chartYLabel = computed(() =>
  storageMode.value ? '相对存储大小（RAW = 100%）' : benchmarkMetricLabel(selectedMetric.value),
)

const runParams = computed(() => {
  const run = currentRun.value
  if (!run) return []
  const cfg = run.config
  const lines = [
    `实验类型：${cfg.kind === 'codec' ? '编码效果实验' : '查询执行实验'}`,
    `数据分布：${distributionLabels[cfg.distribution ?? ''] ?? cfg.distribution ?? '—'}`,
    `行数：${cfg.row_count?.toLocaleString() ?? '—'}`,
    `预热 / 重复：${cfg.warmup_runs} / ${cfg.repeat_runs}`,
    `随机种子：${cfg.seed}`,
  ]
  if (cfg.kind === 'query') lines.push(`数据集 ID：${cfg.dataset_id ?? '—'}`)
  return lines
})
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
        <BenchmarkProgress
          :events="events"
          :progress="progress"
          :status="currentRun?.status ?? null"
        />

        <p v-if="error" class="error">{{ error }}</p>

        <div v-if="currentRun?.status === 'completed'" class="results-body">
          <BenchmarkConclusion
            :run="currentRun"
            :analysis-column="analysisColumn"
            :metrics="summaryMetrics"
          />

          <div v-if="isCodecRun" class="results-toolbar">
            <label>
              分析列
              <select v-model="analysisColumn">
                <option value="qty">qty</option>
                <option value="region">region</option>
              </select>
            </label>
            <label>
              展示指标
              <select v-model="selectedMetric">
                <option v-for="m in metricOptions.length ? metricOptions : ['encoded_bytes']" :key="m" :value="m">
                  {{ benchmarkMetricLabel(m) }}
                </option>
              </select>
            </label>
            <label v-if="!storageMode">
              统计量
              <select v-model="statKey">
                <option value="median">中位数</option>
                <option value="p95">P95</option>
              </select>
            </label>
            <label>
              比较方式
              <select v-model="groupBy">
                <option value="encoding">按编码比较</option>
                <option value="column">按列比较（固定 RAW）</option>
              </select>
            </label>
            <div class="toolbar-actions">
              <button type="button" @click="store.downloadCsv()">导出 CSV</button>
              <button type="button" @click="store.downloadJson()">导出 JSON</button>
            </div>
          </div>

          <BenchmarkChart
            :bars="chartBars"
            :title="chartTitle"
            :y-label="chartYLabel"
            :relative-mode="isCodecRun && storageMode && groupBy === 'encoding'"
          />

          <div class="results-lower">
            <BenchmarkCompareTable
              v-if="storageMode"
              mode="storage"
              :column="analysisColumn"
              :storage-rows="encodingCompareRows"
            />
            <BenchmarkCompareTable
              v-else-if="isTimingBenchmarkMetric(selectedMetric)"
              mode="timing"
              :column="analysisColumn"
              :timing-rows="timingRows"
            />

            <section class="params-panel">
              <h3>实验参数</h3>
              <ul>
                <li v-for="(line, i) in runParams" :key="i">{{ line }}</li>
              </ul>
            </section>
          </div>

          <details v-if="samples.length || currentRun.env" class="advanced-panel">
            <summary>高级详情</summary>
            <div class="advanced-body">
              <section v-if="samples.length">
                <h4>原始样本 ({{ samples.length }})</h4>
                <div class="samples-scroll mono">
                  <div v-for="(s, i) in samples.slice(0, 40)" :key="i" class="sample-line">
                    #{{ s.iteration }} {{ s.phase }} · {{ s.metric_name }} = {{ Math.round(s.value) }}
                  </div>
                </div>
              </section>
              <section v-if="currentRun.env">
                <h4>运行环境</h4>
                <dl class="env-list">
                  <div v-if="currentRun.env.python"><dt>Python</dt><dd class="mono">{{ currentRun.env.python }}</dd></div>
                  <div v-if="currentRun.env.cpu_count"><dt>CPU 逻辑核心</dt><dd class="mono">{{ currentRun.env.cpu_count }}</dd></div>
                  <div v-if="currentRun.env.git_commit"><dt>Git 提交</dt><dd class="mono">{{ currentRun.env.git_commit }}</dd></div>
                </dl>
              </section>
            </div>
          </details>
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
  gap: 12px;
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
  gap: 12px;
}

.results-lower {
  display: grid;
  grid-template-columns: 1fr 240px;
  gap: 10px;
}

.params-panel,
.advanced-panel {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 10px 12px;
  background: var(--bg-panel);
}

.params-panel h3,
.advanced-panel h4 {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
}

.params-panel ul {
  margin: 0;
  padding-left: 16px;
  font-size: 11px;
  color: var(--text-secondary);
}

.advanced-panel summary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.advanced-body {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.samples-scroll {
  max-height: 120px;
  overflow: auto;
  font-size: 10px;
}

.env-list {
  margin: 0;
  font-size: 11px;
}

.env-list div {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 4px;
  padding: 2px 0;
}

.error {
  color: var(--danger);
  font-size: 12px;
}
</style>
