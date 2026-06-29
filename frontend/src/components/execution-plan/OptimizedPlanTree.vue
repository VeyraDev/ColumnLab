<script setup lang="ts">
import { ref } from 'vue'
import type { LogicalPlanNode, OptimizerTraceEntry } from '@/api/queries'
import LogicalPlanTreeNode from './LogicalPlanTreeNode.vue'

defineProps<{
  logicalNode: LogicalPlanNode | null
  optimizedNode: LogicalPlanNode | null
  trace: OptimizerTraceEntry[]
  summary?: string | null
  prunedBlocks?: number
  totalBlocks?: number
}>()

const showOptimized = ref(true)
</script>

<template>
  <section class="optimized-plan">
    <div class="plan-header">
      <span class="plan-title">逻辑计划</span>
      <div class="plan-tabs">
        <button type="button" :class="{ active: !showOptimized }" @click="showOptimized = false">优化前</button>
        <button type="button" :class="{ active: showOptimized }" @click="showOptimized = true">优化后</button>
      </div>
      <span v-if="summary" class="plan-summary mono">{{ summary }}</span>
    </div>
    <p v-if="totalBlocks" class="prune-stats">
      块裁剪：{{ prunedBlocks ?? 0 }} / {{ totalBlocks }} 跳过
    </p>
    <ul v-if="trace.length" class="trace-list">
      <li v-for="(entry, idx) in trace" :key="idx">
        <span class="rule">{{ entry.rule }}</span>
        <span v-if="entry.changed" class="changed">已应用</span>
        <span v-else class="unchanged">未变化</span>
      </li>
    </ul>
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
  padding: 6px 10px;
  background: var(--bg-panel);
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.plan-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.plan-tabs button {
  height: 22px;
  padding: 0 8px;
  border: 1px solid var(--border-default);
  background: var(--bg-muted);
  font-size: 10px;
  cursor: pointer;
}

.plan-tabs button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.plan-summary {
  font-size: 10px;
  color: var(--text-tertiary);
}

.prune-stats {
  margin: 0 0 6px;
  font-size: 10px;
  color: var(--text-secondary);
}

.trace-list {
  margin: 0 0 8px;
  padding: 0;
  list-style: none;
  font-size: 10px;
  color: var(--text-tertiary);
}

.trace-list li {
  display: flex;
  gap: 6px;
  padding: 1px 0;
}

.rule {
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.changed {
  color: #15803d;
}

.unchanged {
  color: var(--text-tertiary);
}

.plan-empty {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
