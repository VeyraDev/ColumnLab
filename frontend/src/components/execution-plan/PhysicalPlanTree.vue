<script setup lang="ts">
import type { LogicalPlanNode } from '@/api/queries'
import LogicalPlanTreeNode from './LogicalPlanTreeNode.vue'

defineProps<{
  node: LogicalPlanNode | null
}>()
</script>

<template>
  <section class="physical-plan">
    <div class="plan-header">
      <span class="plan-title">物理计划</span>
    </div>
    <div v-if="node" class="plan-body">
      <LogicalPlanTreeNode :node="node" physical :is-last="true" />
    </div>
    <p v-else class="plan-empty">执行完成后显示物理算子树</p>
  </section>
</template>

<style scoped>
.physical-plan {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: 8px 10px;
  background: var(--bg-panel);
  border-left: 1px solid var(--border-default);
}

.plan-header {
  margin-bottom: 8px;
}

.plan-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.plan-empty {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
