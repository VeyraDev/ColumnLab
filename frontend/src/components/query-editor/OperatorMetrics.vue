<script setup lang="ts">
import { computed } from 'vue'
import type { OperatorMetric, QueryMetrics } from '@/api/queries'
import { buildExecutionSummary } from '@/utils/executionSummary'
import { formatBytes } from '@/utils/format'
import { operatorLabel, profileMetricLabels } from '@/utils/terminology'

const props = defineProps<{
  metrics: QueryMetrics | null
  operators: OperatorMetric[]
  status?: string | null
  prunedBlocks?: number
  totalBlocks?: number
}>()

function formatNs(ns: number): string {
  if (ns < 1000) return `${ns} ns`
  if (ns < 1_000_000) return `${(ns / 1000).toFixed(1)} µs`
  return `${(ns / 1_000_000).toFixed(2)} ms`
}

const summaryText = computed(() =>
  buildExecutionSummary(props.metrics, props.prunedBlocks, props.totalBlocks),
)

const summaryItems = computed(() => {
  const m = props.metrics
  if (!m) return []
  const items: Array<{ label: string; value: string; hint?: string }> = []
  const push = (key: keyof typeof profileMetricLabels, value: number | undefined, formatter?: (v: number) => string) => {
    if (value == null) return
    items.push({
      label: profileMetricLabels[key],
      value: formatter ? formatter(value) : String(value),
      hint: key,
    })
  }
  push('block_accesses', (m as { block_accesses?: number }).block_accesses)
  push('scanned_blocks', m.scanned_blocks)
  push('cache_hits', m.cache_hits)
  push('compressed_operator_blocks', m.compressed_operator_blocks)
  push('decoded_blocks', m.decoded_blocks)
  push('rows_output', m.rows_output)
  push('bytes_read', m.bytes_read, formatBytes)
  return items
})
</script>

<template>
  <section class="operator-metrics">
    <div class="metrics-header">
      <span class="metrics-title">执行 Profile</span>
      <span v-if="status" class="status-badge" :data-status="status">{{ status }}</span>
    </div>

    <p v-if="summaryText" class="exec-summary">{{ summaryText }}</p>

    <ul v-if="summaryItems.length" class="summary-grid">
      <li v-for="item in summaryItems" :key="item.label">
        <span class="label">{{ item.label }}</span>
        <span class="value mono">{{ item.value }}</span>
        <span v-if="item.hint" class="hint mono">{{ item.hint }}</span>
      </li>
    </ul>

    <table v-if="operators.length" class="ops-table">
      <thead>
        <tr>
          <th>执行步骤</th>
          <th>块内行数</th>
          <th>匹配/输出行数</th>
          <th>耗时</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="op in operators" :key="op.operator_id">
          <td :title="op.operator_type">{{ operatorLabel(op.operator_type) }}</td>
          <td>{{ op.input_rows }}</td>
          <td>{{ op.output_rows }}</td>
          <td class="mono">{{ formatNs(op.elapsed_ns) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="metrics-empty">运行查询后显示算子级指标</p>
  </section>
</template>

<style scoped>
.operator-metrics {
  padding: 10px 12px;
  background: var(--bg-panel);
  overflow: auto;
}

.metrics-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.metrics-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
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

.exec-summary {
  margin: 0 0 10px;
  padding: 8px 10px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-muted);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
  font-size: 12px;
}

.summary-grid li {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2px 8px;
  align-items: baseline;
}

.summary-grid .label {
  color: var(--text-secondary);
}

.summary-grid .value {
  text-align: right;
  color: var(--text-primary);
  font-weight: 600;
}

.summary-grid .hint {
  grid-column: 2;
  font-size: 10px;
  color: var(--text-muted);
  text-align: right;
}

.ops-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.ops-table th,
.ops-table td {
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.ops-table th {
  color: var(--text-secondary);
  font-weight: 500;
}

.metrics-empty {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
