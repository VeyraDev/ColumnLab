<script setup lang="ts">
import { computed } from 'vue'
import { encodingShortLabel, formatBlockLabel } from '@/utils/format'
import { BLOCK_CELL_HEIGHT, BLOCK_CELL_WIDTH } from './blockWindow'

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
const idLabel = computed(() =>
  props.blockId != null ? formatBlockLabel(props.blockId) : '—',
)
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
    :style="{
      width: `${cellWidth ?? BLOCK_CELL_WIDTH}px`,
      height: `${BLOCK_CELL_HEIGHT}px`,
    }"
    :title="`${encoding} #${blockId ?? '?'} · ${rowCount ?? '?'} rows`"
    :aria-label="`${encoding} block ${blockId}`"
    :aria-pressed="active"
    @click="$emit('select')"
  >
    <span class="cell-id mono">{{ idLabel }}</span>
    <span class="cell-enc mono">{{ label }}</span>
  </button>
</template>

<style scoped>
.block-cell {
  padding: 1px 2px;
  border: 1px solid var(--border-default);
  border-radius: 2px;
  cursor: pointer;
  flex-shrink: 0;
  background-color: var(--bg-panel);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  overflow: hidden;
}

.cell-id {
  font-size: 9px;
  line-height: 1.1;
  color: var(--text-secondary);
  pointer-events: none;
}

.cell-enc {
  font-size: 8px;
  line-height: 1.1;
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
  outline-offset: -1px;
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
}

.block-cell.skipped::after,
.block-cell.metadata_check::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    -45deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.04) 2px,
    rgba(0, 0, 0, 0.04) 3px
  );
}

.block-cell {
  position: relative;
}

.block-cell.to_read {
  outline: 1px dashed var(--state-active-border);
  outline-offset: -1px;
}
</style>
