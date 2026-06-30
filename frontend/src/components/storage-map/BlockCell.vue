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
  position: relative;
  padding: 2px 3px;
  border: 1px solid var(--border-default);
  border-radius: 3px;
  cursor: pointer;
  flex-shrink: 0;
  background-color: var(--bg-raised);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  overflow: hidden;
}

.block-cell::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.26;
  z-index: 0;
}

.cell-id {
  position: relative;
  z-index: 1;
  font-size: 10px;
  line-height: 1.1;
  font-weight: 600;
  color: var(--text-primary);
  pointer-events: none;
}

.cell-enc {
  position: relative;
  z-index: 1;
  font-size: 9px;
  line-height: 1.1;
  color: var(--text-body);
  pointer-events: none;
}

.block-cell.raw::before {
  background: repeating-linear-gradient(
    -45deg,
    var(--text-muted),
    var(--text-muted) 1px,
    transparent 1px,
    transparent 6px
  );
}

.block-cell.rle::before {
  background: repeating-linear-gradient(
    0deg,
    var(--text-muted),
    var(--text-muted) 1px,
    transparent 1px,
    transparent 5px
  );
}

.block-cell.dictionary::before,
.block-cell.dict::before {
  background:
    radial-gradient(circle, var(--text-muted) 1px, transparent 1px);
  background-size: 6px 6px;
}

.block-cell.selected {
  outline: 1px solid var(--text-body);
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
  z-index: 2;
  pointer-events: none;
  background: repeating-linear-gradient(
    -45deg,
    transparent,
    transparent 3px,
    rgba(0, 0, 0, 0.06) 3px,
    rgba(0, 0, 0, 0.06) 4px
  );
}

.block-cell.to_read {
  outline: 1px dashed var(--state-active-border);
  outline-offset: -1px;
}
</style>
