<script setup lang="ts">
import { computed } from 'vue'
import { encodingShortLabel } from '@/utils/format'

const props = defineProps<{
  encoding: string
  blockId?: number
  rowCount?: number
  cellWidth?: number
  selected?: boolean
  active?: boolean
  scanned?: boolean
  pruneState?: string
}>()

defineEmits<{
  select: []
}>()

const label = computed(() => encodingShortLabel(props.encoding))
</script>

<template>
  <button
    type="button"
    class="block-cell"
    :class="[
      encoding.toLowerCase(),
      pruneState,
      { selected, active, scanned },
    ]"
    :style="{ width: `${cellWidth ?? 32}px`, height: `${cellWidth ?? 32}px` }"
    :title="`${encoding} #${blockId ?? '?'} · ${rowCount ?? '?'} rows`"
    :aria-label="`${encoding} block ${blockId}`"
    :aria-pressed="active"
    @click="$emit('select')"
  >
    <span class="cell-label">{{ label }}</span>
  </button>
</template>

<style scoped>
.block-cell {
  padding: 0;
  border: 1px solid var(--border-default);
  border-radius: 2px;
  cursor: pointer;
  flex-shrink: 0;
  background-color: var(--bg-panel);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.cell-label {
  font-size: 8px;
  line-height: 1;
  font-family: var(--font-mono);
  color: var(--text-tertiary);
  pointer-events: none;
}

.block-cell.raw {
  background: repeating-linear-gradient(
    -45deg,
    var(--bg-muted),
    var(--bg-muted) 2px,
    var(--bg-panel) 2px,
    var(--bg-panel) 4px
  );
}

.block-cell.rle {
  background: repeating-linear-gradient(
    0deg,
    var(--bg-muted),
    var(--bg-muted) 2px,
    var(--bg-panel) 2px,
    var(--bg-panel) 4px
  );
}

.block-cell.dictionary,
.block-cell.dict {
  background:
    radial-gradient(circle, var(--text-tertiary) 1px, transparent 1px);
  background-size: 4px 4px;
  background-color: var(--bg-panel);
}

.block-cell.selected {
  outline: 1px solid var(--text-secondary);
}

.block-cell.scanned {
  border-color: var(--state-scanned-border);
}

.block-cell.active {
  border: 2px solid var(--state-active-border);
  background-color: var(--state-active-bg);
}

.block-cell.skipped,
.block-cell.metadata_check {
  opacity: var(--state-skipped-opacity);
  background: repeating-linear-gradient(
    -45deg,
    var(--bg-muted),
    var(--bg-muted) 1px,
    transparent 1px,
    transparent 3px
  ) !important;
}

.block-cell.to_read {
  outline: 1px dashed var(--state-active-border);
}
</style>
