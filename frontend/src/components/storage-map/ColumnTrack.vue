<script setup lang="ts">
import { computed } from 'vue'
import BlockCell from './BlockCell.vue'

export type StorageBlock = {
  block_id: number
  row_group_id?: number
  encoding: string
  row_start: number
  row_count: number
  compressed_bytes: number
  encoded_bytes: number
  raw_bytes: number
  null_count: number
  payload_crc32: string
}

const props = defineProps<{
  name: string
  blocks: StorageBlock[]
  blocksPerRow: number
  cellWidth: number
  visibleStart: number
  visibleEnd: number
  selectedBlockId?: number | null
  activeBlockId?: number | null
  blockPruningMap?: Record<string, { state: string; reason: string }>
}>()

const emit = defineEmits<{
  selectBlock: [block: StorageBlock]
}>()

const labelWidth = 96
const gap = 4

const trackWidth = computed(() => {
  const cols = Math.min(props.blocksPerRow, props.blocks.length || 1)
  return cols * props.cellWidth + Math.max(0, cols - 1) * gap
})

const visibleBlocks = computed(() => {
  const start = Math.max(0, Math.min(props.visibleStart, props.blocks.length))
  const end = Math.min(props.blocks.length, props.visibleEnd + 1)
  return props.blocks.slice(start, end)
})

const topSpacerHeight = computed(() => {
  const hiddenRows = Math.floor(props.visibleStart / props.blocksPerRow)
  return hiddenRows * (22 + gap)
})

function chunkBlocks(blocks: StorageBlock[]) {
  const rows: StorageBlock[][] = []
  for (let i = 0; i < blocks.length; i += props.blocksPerRow) {
    rows.push(blocks.slice(i, i + props.blocksPerRow))
  }
  return rows
}

const blockRows = computed(() => chunkBlocks(visibleBlocks.value))

function pruneState(column: string, blockId: number) {
  return props.blockPruningMap?.[`${column}:${blockId}`]?.state
}

function isScanned(column: string, blockId: number) {
  const state = pruneState(column, blockId)
  return state === 'to_read' || state === 'scanned'
}
</script>

<template>
  <div class="column-track">
    <div class="track-header" :style="{ width: `${labelWidth}px` }">
      <span class="track-label">{{ name }}</span>
      <span class="track-count">{{ blocks.length }} 块</span>
    </div>
    <div class="track-grid" :style="{ width: `${trackWidth}px` }">
      <div v-if="topSpacerHeight > 0" class="track-spacer" :style="{ height: `${topSpacerHeight}px` }" />
      <div v-for="(row, rowIdx) in blockRows" :key="rowIdx" class="track-row">
        <BlockCell
          v-for="block in row"
          :key="block.block_id"
          :encoding="block.encoding"
          :block-id="block.block_id"
          :row-count="block.row_count"
          :cell-width="cellWidth"
          :prune-state="pruneState(name, block.block_id)"
          :scanned="isScanned(name, block.block_id)"
          :selected="selectedBlockId === block.block_id"
          :active="activeBlockId === block.block_id"
          @select="emit('selectBlock', block)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.column-track {
  display: grid;
  grid-template-columns: 96px max-content;
  gap: 8px;
  align-items: start;
  min-height: 22px;
}

.track-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding-top: 2px;
}

.track-label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-count {
  font-size: 10px;
  color: var(--text-tertiary);
}

.track-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.track-row {
  display: flex;
  gap: 4px;
  flex-wrap: nowrap;
}
</style>
