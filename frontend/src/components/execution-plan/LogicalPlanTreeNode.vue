<script setup lang="ts">
import { computed } from 'vue'
import type { LogicalPlanNode } from '@/api/queries'
import { formatPlanNodeLabel, operatorLabel } from '@/utils/terminology'

const props = withDefaults(
  defineProps<{
    node: LogicalPlanNode
    depth?: number
    physical?: boolean
    isLast?: boolean
    prefix?: string
  }>(),
  { depth: 0, physical: false, isLast: true, prefix: '' },
)

const display = computed(() => formatPlanNodeLabel(props.node))

const branchPrefix = computed(() => {
  if (!props.physical) return ''
  return props.prefix + (props.isLast ? '└─ ' : '├─ ')
})

const childPrefix = computed(() => {
  if (!props.physical) return props.prefix
  return props.prefix + (props.isLast ? '   ' : '│  ')
})

const children = computed(() => props.node.children ?? [])
</script>

<template>
  <div class="plan-node" :class="{ physical }">
    <div v-if="physical" class="plan-line physical-line">
      <span class="branch mono">{{ branchPrefix }}</span>
      <span class="primary">{{ display.primary.split('\n')[0] }}</span>
      <span v-if="display.secondary && display.secondary !== display.primary.split('\n')[0]" class="secondary mono">
        {{ display.secondary }}
      </span>
    </div>
    <div v-else class="plan-line logical-line">
      <span class="indent mono">{{ '  '.repeat(depth) }}</span>
      <span class="primary">{{ operatorLabel(node.type) }}</span>
      <template v-if="node.type === 'Scan'">
        <span class="detail"> table={{ node.details.table }}</span>
        <span
          v-if="Array.isArray((node.details.annotations as Record<string, unknown> | undefined)?.required_columns)"
          class="detail"
        >
          · 需要列：{{
            ((node.details.annotations as Record<string, unknown>).required_columns as string[]).join('、')
          }}
        </span>
      </template>
      <template v-else-if="node.type === 'BlockScan'">
        <span class="detail"> column={{ node.details.column }}</span>
      </template>
      <template v-else-if="node.type === 'Limit'">
        <span class="detail"> limit={{ node.details.limit }} offset={{ node.details.offset }}</span>
      </template>
      <span v-if="display.secondary && display.secondary !== node.type" class="secondary mono">{{ node.type }}</span>
    </div>
    <p
      v-if="physical && display.primary.includes('\n')"
      class="sub-line"
      :style="{ paddingLeft: `${branchPrefix.length * 7 + 8}px` }"
    >
      {{ display.primary.split('\n').slice(1).join(' ') }}
    </p>
    <p
      v-else-if="!physical && display.primary.includes('\n')"
      class="sub-line"
      :style="{ paddingLeft: `${depth * 12 + 12}px` }"
    >
      {{ display.primary.split('\n').slice(1).join(' ') }}
    </p>
    <LogicalPlanTreeNode
      v-for="(child, idx) in children"
      :key="idx"
      :node="child"
      :depth="depth + 1"
      :physical="physical"
      :is-last="idx === children.length - 1"
      :prefix="physical ? childPrefix : ''"
    />
  </div>
</template>

<script lang="ts">
export default { name: 'LogicalPlanTreeNode' }
</script>

<style scoped>
.plan-line {
  font-size: 12px;
  line-height: 1.65;
  color: var(--text-primary);
}

.physical-line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px;
}

.branch {
  color: var(--text-muted);
  flex-shrink: 0;
}

.primary {
  font-weight: 500;
}

.detail {
  color: var(--text-secondary);
}

.secondary {
  font-size: 10px;
  color: var(--text-muted);
}

.sub-line {
  margin: 0;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
}
</style>
