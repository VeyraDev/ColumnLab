<script setup lang="ts">
import type { LogicalPlanNode } from '@/api/queries'

withDefaults(
  defineProps<{
    node: LogicalPlanNode
    depth?: number
  }>(),
  { depth: 0 },
)
</script>

<template>
  <div class="plan-node">
    <div class="plan-line mono">
      {{ '  '.repeat(depth) }}{{ node.type }}
      <template v-if="node.type === 'Scan'"> table={{ node.details.table }}</template>
      <template v-else-if="node.type === 'BlockScan'"> column={{ node.details.column }}</template>
      <template v-else-if="node.type === 'Limit'">
        limit={{ node.details.limit }} offset={{ node.details.offset }}
      </template>
    </div>
    <LogicalPlanTreeNode
      v-for="(child, idx) in node.children"
      :key="idx"
      :node="child"
      :depth="depth + 1"
    />
  </div>
</template>

<script lang="ts">
export default { name: 'LogicalPlanTreeNode' }
</script>

<style scoped>
.plan-line {
  font-size: 11px;
  line-height: 1.6;
  color: var(--text-primary);
}
</style>
