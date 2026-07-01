<script setup lang="ts">
import { computed, ref } from 'vue'
import type { LogicalPlanNode, OptimizerTraceEntry } from '@/api/queries'
import { buildBlockPruningStats } from '@/utils/executionSummary'
import {
  optimizerLabel,
  optimizerStatusLabels,
  optimizerSummarySentence,
} from '@/utils/terminology'
import LogicalPlanTreeNode from './LogicalPlanTreeNode.vue'

const props = defineProps<{
  logicalNode: LogicalPlanNode | null
  optimizedNode: LogicalPlanNode | null
  trace: OptimizerTraceEntry[]
  summary?: string | null
  prunedBlocks?: number
  totalBlocks?: number
}>()

const showOptimized = ref(true)

const traceRows = computed(() => {
  const knownRules = [
    'projection_pruning',
    'constant_folding',
    'predicate_normalization',
    'predicate_pushdown',
    'aggregate_pushdown',
    'limit_pushdown',
  ]
  const byRule = new Map(props.trace.map((e) => [e.rule, e]))
  return knownRules.map((rule) => {
    const entry = byRule.get(rule)
    if (entry?.changed) return { rule, label: optimizerLabel(rule), status: optimizerStatusLabels.applied }
    if (entry && !entry.changed) return { rule, label: optimizerLabel(rule), status: optimizerStatusLabels.unchanged }
    return { rule, label: optimizerLabel(rule), status: optimizerStatusLabels.notApplicable }
  })
})

const appliedRules = computed(() => props.trace.filter((e) => e.changed).map((e) => e.rule))

const optimizationSummary = computed(() => optimizerSummarySentence(appliedRules.value))

const pruningStats = computed(() => {
  if (!props.totalBlocks) return null
  return buildBlockPruningStats(props.prunedBlocks ?? 0, props.totalBlocks)
})
</script>

<template>
  <section class="optimized-plan">
    <div class="plan-header">
      <span class="plan-title">逻辑计划</span>
      <div class="plan-tabs">
        <button type="button" :class="{ active: !showOptimized }" @click="showOptimized = false">优化前</button>
        <button type="button" :class="{ active: showOptimized }" @click="showOptimized = true">优化后</button>
      </div>
    </div>

    <section v-if="pruningStats" class="pruning-panel">
      <div class="pruning-title">块裁剪结果</div>
      <dl class="pruning-grid">
        <div><dt>候选列块</dt><dd class="mono">{{ pruningStats.totalBlocks }}</dd></div>
        <div><dt>提前排除</dt><dd class="mono">{{ pruningStats.prunedBlocks }}</dd></div>
        <div><dt>进入执行</dt><dd class="mono">{{ pruningStats.entered }}</dd></div>
        <div><dt>裁剪率</dt><dd class="mono">{{ pruningStats.rate.toFixed(1) }}%</dd></div>
      </dl>
      <p class="pruning-note">
        被排除的列块与查询条件的数值范围或字典内容不相交，因此无需读取编码载荷。
      </p>
    </section>

    <section v-if="trace.length" class="trace-panel">
      <div class="trace-title">优化规则</div>
      <ul class="trace-list">
        <li v-for="row in traceRows" :key="row.rule">
          <span class="rule">{{ row.label }}</span>
          <span class="status" :class="{ applied: row.status === optimizerStatusLabels.applied }">{{ row.status }}</span>
        </li>
      </ul>
      <p class="opt-summary">{{ optimizationSummary }}</p>
    </section>

    <div v-if="showOptimized ? optimizedNode : logicalNode" class="plan-body">
      <LogicalPlanTreeNode :node="(showOptimized ? optimizedNode : logicalNode)!" />
    </div>
    <p v-else class="plan-empty">运行查询后在此显示逻辑计划树</p>
  </section>
</template>

<style scoped>
.optimized-plan {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: 8px 10px;
  background: var(--bg-panel);
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.plan-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.plan-tabs button {
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--border-default);
  background: var(--bg-muted);
  font-size: 11px;
  cursor: pointer;
}

.plan-tabs button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.pruning-panel,
.trace-panel {
  margin-bottom: 10px;
  padding: 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--bg-muted);
}

.pruning-title,
.trace-title {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.pruning-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  margin: 0;
  font-size: 11px;
}

.pruning-grid div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pruning-grid dt {
  color: var(--text-tertiary);
}

.pruning-grid dd {
  margin: 0;
  font-weight: 600;
  color: var(--text-primary);
}

.pruning-note,
.opt-summary {
  margin: 6px 0 0;
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.trace-list {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 11px;
}

.trace-list li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 0;
}

.rule {
  color: var(--text-primary);
}

.status {
  color: var(--text-muted);
  flex-shrink: 0;
}

.status.applied {
  color: var(--success);
  font-weight: 600;
}

.plan-empty {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
