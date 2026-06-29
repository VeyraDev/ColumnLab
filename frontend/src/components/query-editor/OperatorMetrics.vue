<script setup lang="ts">
import { computed } from 'vue'
import type { OperatorMetric, QueryMetrics } from '@/api/queries'

const props = defineProps<{
  metrics: QueryMetrics | null
  operators: OperatorMetric[]
  status?: string | null
}>()

function formatNs(ns: number): string {
  if (ns < 1000) return `${ns} ns`
  if (ns < 1_000_000) return `${(ns / 1000).toFixed(1)} µs`
  return `${(ns / 1_000_000).toFixed(2)} ms`
}

const summary = computed(() => {
  const m = props.metrics
  if (!m) return null
  return [
    { label: '扫描块', value: m.scanned_blocks },
    { label: '跳过块', value: m.pruned_blocks },
    { label: '缓存命中', value: m.cache_hits },
    { label: '压缩态块', value: m.compressed_operator_blocks },
    { label: '解码块', value: m.decoded_blocks },
    { label: '输出行', value: m.rows_output },
  ]
})
</script>

<template>
  <section class="operator-metrics">
    <div class="metrics-header">
      <span class="metrics-title">执行指标</span>
      <span v-if="status" class="status-badge" :data-status="status">{{ status }}</span>
    </div>
    <ul v-if="summary" class="summary-grid">
      <li v-for="item in summary" :key="item.label">
        <span class="label">{{ item.label }}</span>
        <span class="value mono">{{ item.value }}</span>
      </li>
    </ul>
    <table v-if="operators.length" class="ops-table">
      <thead>
        <tr>
          <th>算子</th>
          <th>输入</th>
          <th>输出</th>
          <th>耗时</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="op in operators" :key="op.operator_id">
          <td class="mono">{{ op.operator_type }}</td>
          <td>{{ op.input_rows }}</td>
          <td>{{ op.output_rows }}</td>
          <td>{{ formatNs(op.elapsed_ns) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="metrics-empty">运行查询后显示算子级指标</p>
  </section>
</template>

<style scoped>
.operator-metrics {
  padding: 6px 10px;
  background: var(--bg-panel);
  border-top: 1px solid var(--border-default);
  overflow: auto;
  max-height: 140px;
}

.metrics-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.metrics-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.status-badge {
  font-size: 10px;
  padding: 1px 6px;
  border: 1px solid var(--border-default);
  text-transform: uppercase;
}

.status-badge[data-status='completed'] {
  color: #15803d;
}

.status-badge[data-status='running'] {
  color: #b45309;
}

.summary-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin: 0 0 8px;
  padding: 0;
  list-style: none;
  font-size: 10px;
}

.summary-grid .label {
  color: var(--text-tertiary);
  margin-right: 4px;
}

.ops-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10px;
}

.ops-table th,
.ops-table td {
  text-align: left;
  padding: 2px 6px;
  border-bottom: 1px solid var(--border-subtle);
}

.metrics-empty {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
