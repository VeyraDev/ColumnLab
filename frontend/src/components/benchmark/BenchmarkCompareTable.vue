<script setup lang="ts">
import { computed } from 'vue'
import { encodingLabel } from '@/utils/terminology'
import { formatBytes } from '@/utils/format'

export type StorageRow = {
  encoding: string
  encodedBytes: number
  relativePercent: number
  savedPercent: number
}

export type TimingRow = {
  encoding: string
  median: number
  p95: number
  stdev: number
}

const props = defineProps<{
  mode: 'storage' | 'timing'
  storageRows?: StorageRow[]
  timingRows?: TimingRow[]
  column?: string
}>()

function formatTiming(ns: number): string {
  if (ns < 1000) return `${Math.round(ns)} ns`
  if (ns < 1_000_000) return `${(ns / 1000).toFixed(1)} µs`
  return `${(ns / 1_000_000).toFixed(2)} ms`
}

const title = computed(() =>
  props.mode === 'storage'
    ? `${props.column ?? ''} 列编码方案对比`
    : `${props.column ?? ''} 列编码耗时对比`,
)
</script>

<template>
  <section class="compare-table">
    <h2>{{ title }}</h2>
    <table v-if="mode === 'storage' && storageRows?.length">
      <thead>
        <tr>
          <th>编码方案</th>
          <th>编码后大小</th>
          <th>相对 RAW 大小</th>
          <th>节省空间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in storageRows" :key="row.encoding">
          <td>{{ encodingLabel(row.encoding) }}</td>
          <td class="mono">{{ formatBytes(row.encodedBytes) }}</td>
          <td class="mono">{{ row.relativePercent.toFixed(1) }}%</td>
          <td class="mono">{{ row.savedPercent.toFixed(1) }}%</td>
        </tr>
      </tbody>
    </table>
    <table v-else-if="mode === 'timing' && timingRows?.length">
      <thead>
        <tr>
          <th>编码方案</th>
          <th>中位数</th>
          <th>P95</th>
          <th>标准差</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in timingRows" :key="row.encoding">
          <td>{{ encodingLabel(row.encoding) }}</td>
          <td class="mono">{{ formatTiming(row.median) }}</td>
          <td class="mono">{{ formatTiming(row.p95) }}</td>
          <td class="mono">{{ formatTiming(row.stdev) }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.compare-table {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 10px 12px;
  background: var(--bg-panel);
}

h2 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

th,
td {
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-subtle);
}

th {
  color: var(--text-secondary);
  font-weight: 500;
}
</style>
