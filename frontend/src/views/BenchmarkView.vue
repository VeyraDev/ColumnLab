<script setup lang="ts">
import { storeToRefs } from 'pinia'
import PageBackNav from '@/components/workspace/PageBackNav.vue'
import BenchmarkChart from '@/components/benchmark/BenchmarkChart.vue'
import BenchmarkCompareTable from '@/components/benchmark/BenchmarkCompareTable.vue'
import BenchmarkConclusion from '@/components/benchmark/BenchmarkConclusion.vue'
import BenchmarkConfigurator from '@/components/benchmark/BenchmarkConfigurator.vue'
import BenchmarkProgress from '@/components/benchmark/BenchmarkProgress.vue'
import { useBenchmarkStore } from '@/stores/benchmarkStore'

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
} = storeToRefs(store)
</script>

<template>
  <div class="benchmark-view">
    <PageBackNav label="返回工作区" />
    <header class="bench-header">
      <h1>性能基准中心</h1>
      <p class="subtitle">可重复 codec / query 实验，汇总 mean / median / p95 / stdev</p>
    </header>

    <BenchmarkConfigurator v-model:config="config">
      <div class="actions">
        <button type="button" class="primary" :disabled="loading" @click="store.runBenchmark()">
          {{ loading ? '运行中…' : '提交实验' }}
        </button>
        <button type="button" :disabled="!currentRun" @click="store.downloadCsv()">导出 CSV</button>
        <button type="button" :disabled="!currentRun" @click="store.downloadJson()">导出 JSON</button>
      </div>
    </BenchmarkConfigurator>

    <BenchmarkProgress
      :events="events"
      :progress="progress"
      :status="currentRun?.status ?? null"
    />

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="currentRun?.status === 'completed'" class="results">
      <BenchmarkCompareTable :rows="encodedBytesRows" />
      <BenchmarkChart :rows="encodedBytesRows" />
      <BenchmarkConclusion :run="currentRun" :comparison="comparison" />
    </div>
  </div>
</template>

<style scoped>
.benchmark-view {
  padding: 16px 20px;
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bench-header h1 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
}

.subtitle {
  margin: 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

button {
  font-size: 12px;
  padding: 6px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-muted);
  cursor: pointer;
}

button.primary {
  background: var(--state-active-bg, #eef3fa);
  border-color: var(--state-active-border, #4a6fa5);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.error {
  color: var(--state-error-text, #b42318);
  font-size: 12px;
}
</style>
