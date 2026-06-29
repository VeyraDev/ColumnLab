<script setup lang="ts">
import { computed } from 'vue'
import type { LogicalPlanNode, OperatorMetric, QueryMetrics } from '@/api/queries'
import LogicalPlanTreeNode from './LogicalPlanTreeNode.vue'

const props = defineProps<{
  status?: string | null
  physicalPlanTree: LogicalPlanNode | null
  metrics: QueryMetrics | null
  operators: OperatorMetric[]
  prunedBlocks?: number
  totalBlocks?: number
}>()

const summary = computed(() => {
  const m = props.metrics
  if (!m) return null
  return {
    scanned: m.scanned_blocks,
    pruned: m.pruned_blocks,
    cacheHits: m.cache_hits,
    rowsOut: m.rows_output,
    compressed: m.compressed_operator_blocks,
    decoded: m.decoded_blocks,
  }
})
</script>

<template>
  <section class="execution-trace">
    <div class="trace-header">
      <span class="trace-title">执行轨迹</span>
      <span v-if="status" class="status mono">{{ status }}</span>
    </div>
    <div v-if="summary" class="stats-row">
      <span>扫描 {{ summary.scanned }}</span>
      <span>跳过 {{ summary.pruned ?? prunedBlocks ?? 0 }}</span>
      <span>缓存 {{ summary.cacheHits }}</span>
      <span>输出 {{ summary.rowsOut }}</span>
      <span>压缩态 {{ summary.compressed }}</span>
      <span>解码 {{ summary.decoded }}</span>
    </div>
    <div v-if="physicalPlanTree" class="plan-snippet">
      <LogicalPlanTreeNode :node="physicalPlanTree" />
    </div>
    <ul v-if="operators.length" class="op-list">
      <li v-for="op in operators" :key="op.operator_id">
        <span class="mono">{{ op.operator_type }}</span>
        <span>{{ op.input_rows }} → {{ op.output_rows }}</span>
        <span class="mono">{{ (op.elapsed_ns / 1000).toFixed(0) }} µs</span>
      </li>
    </ul>
    <p v-else class="empty">运行查询后显示物理计划与算子轨迹</p>
  </section>
</template>

<style scoped>
.execution-trace {
  padding: 6px 10px;
  background: var(--bg-muted);
  border-top: 1px solid var(--border-default);
  max-height: 120px;
  overflow: auto;
}

.trace-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
}

.trace-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.status {
  font-size: 10px;
  color: var(--text-tertiary);
}

.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 10px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.plan-snippet {
  font-size: 10px;
  max-height: 48px;
  overflow: hidden;
}

.op-list {
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
  font-size: 10px;
}

.op-list li {
  display: flex;
  gap: 8px;
  padding: 1px 0;
  color: var(--text-tertiary);
}

.empty {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
