<script setup lang="ts">
import type { LogicalPlanNode } from '@/api/queries'
import LogicalPlanTreeNode from './LogicalPlanTreeNode.vue'

import type { QueryError } from '@/api/queries'

defineProps<{
  node: LogicalPlanNode | null
  summary?: string | null
  error?: QueryError | null
}>()
</script>

<template>
  <section class="logical-plan">
    <div class="plan-header">
      <span class="plan-title">逻辑计划</span>
      <span v-if="summary" class="plan-summary mono">{{ summary }}</span>
    </div>
    <div v-if="node" class="plan-body">
      <LogicalPlanTreeNode :node="node" />
    </div>
    <p v-else-if="error" class="plan-error mono">{{ error.message }}</p>
    <p v-else class="plan-empty">运行查询后在此显示逻辑计划树</p>
  </section>
</template>

<style scoped>
.logical-plan {
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
}

.plan-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.plan-summary {
  font-size: 10px;
  color: var(--text-tertiary);
}

.plan-empty {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
}

.plan-error {
  margin: 0;
  font-size: 11px;
  color: #b91c1c;
}
</style>
