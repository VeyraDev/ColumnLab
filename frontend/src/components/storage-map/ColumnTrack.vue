<script setup lang="ts">
import { computed } from 'vue'
import BlockCell from './BlockCell.vue'
import type { BlockWindowItem } from './blockWindow'
import { BLOCK_CELL_WIDTH, TRACK_LABEL_WIDTH } from './blockWindow'
import { displayLogicalType } from '@/utils/format'

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
  logicalType?: string
  blocks: StorageBlock[]
  blockWindow: BlockWindowItem[]
  selectedBlockId?: number | null
  activeBlockId?: number | null
  blockPruningMap?: Record<string, { state: string; reason: string }>
}>()

const emit = defineEmits<{
  selectBlock: [block: StorageBlock]
}>()

const typeLabel = computed(() =>
  props.logicalType ? displayLogicalType(props.logicalType) : '',
)

function pruneState(column: string, blockId: number) {
  return props.blockPruningMap?.[`${column}:${blockId}`]?.state
}

function isScanned(column: string, blockId: number) {
  const state = pruneState(column, blockId)
  return state === 'to_read' || state === 'scanned'
}

function blockAt(index: number) {
  return props.blocks[index]
}

function onSelect(index: number) {
  const block = blockAt(index)
  if (block) emit('selectBlock', block)
}
</script>

<template>
  <div class="column-track">
    <div class="track-label" :style="{ width: `${TRACK_LABEL_WIDTH}px` }">
      <span class="track-name mono">{{ name }}</span>
      <span v-if="typeLabel" class="track-type mono">{{ typeLabel }}</span>
    </div>
    <div class="track-blocks">
      <template v-for="(item, idx) in blockWindow" :key="`${item.kind}-${idx}`">
        <span v-if="item.kind === 'ellipsis'" class="track-ellipsis" aria-hidden="true">…</span>
        <BlockCell
          v-else
          :encoding="blockAt(item.index)?.encoding ?? 'RAW'"
          :block-id="item.index"
          :row-count="blockAt(item.index)?.row_count"
          :cell-width="BLOCK_CELL_WIDTH"
          :prune-state="pruneState(name, item.index)"
          :scanned="isScanned(name, item.index)"
          :selected="selectedBlockId === item.index"
          :active="activeBlockId === item.index"
          @select="onSelect(item.index)"
        />
      </template>
    </div>
  </div>
</template>

<style scoped>
.column-track {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  height: 32px;
  min-height: 32px;
}

.track-label {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  overflow: hidden;
}

.track-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-type {
  font-size: 9px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-blocks {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 3px;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
}

.track-blocks::-webkit-scrollbar {
  display: none;
}

.track-ellipsis {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
  font-size: 11px;
  color: var(--text-tertiary);
  user-select: none;
}
</style>
