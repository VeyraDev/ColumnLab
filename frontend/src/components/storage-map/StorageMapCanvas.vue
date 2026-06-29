<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import ColumnTrack, { type StorageBlock } from './ColumnTrack.vue'
import MapEncodingLegend from '@/components/workspace/MapEncodingLegend.vue'
import { useStorageMapStore } from '@/stores/storageMapStore'
import { useStorageMapViewStore } from '@/stores/storageMapViewStore'
import { formatBlockLabel } from '@/utils/format'
import type { BlockPruningState } from '@/api/queries'

const ROW_HEIGHT = 26
const WINDOW_BUFFER_ROWS = 3

const props = defineProps<{
  datasetId?: string
  blockPruning?: BlockPruningState[]
  activeScanBlock?: { column: string; block_id: number } | null
}>()

const emit = defineEmits<{
  selectBlock: [payload: { column: string; block: StorageBlock }]
}>()

const mapStore = useStorageMapStore()
const viewStore = useStorageMapViewStore()
const { mapData, loading, error, hasData } = storeToRefs(mapStore)
const { blocksPerRow } = storeToRefs(viewStore)

const blockPruningMap = computed(() => {
  const map: Record<string, { state: string; reason: string }> = {}
  for (const entry of props.blockPruning ?? []) {
    map[`${entry.column}:${entry.block_id}`] = { state: entry.state, reason: entry.reason }
  }
  return map
})

const scrollRoot = ref<HTMLElement | null>(null)
const cellWidth = 32
const labelWidth = 96
const labelGap = 8
const visibleBlockStart = ref(0)
const visibleBlockEnd = ref(64)

const data = computed(() => mapData.value)

const maxBlocks = computed(() =>
  Math.max(...(data.value?.columns.map((col) => col.blocks.length) ?? [0]), 0),
)

function updateVisibleWindow() {
  const el = scrollRoot.value
  if (!el || maxBlocks.value === 0) return
  const perRow = Math.max(1, blocksPerRow.value)
  const startRow = Math.max(0, Math.floor(el.scrollTop / ROW_HEIGHT) - WINDOW_BUFFER_ROWS)
  const visibleRows =
    Math.ceil(el.clientHeight / ROW_HEIGHT) + WINDOW_BUFFER_ROWS * 2
  const startBlock = startRow * perRow
  const endBlock = Math.min(maxBlocks.value - 1, startBlock + visibleRows * perRow - 1)
  visibleBlockStart.value = startBlock
  visibleBlockEnd.value = Math.max(startBlock, endBlock)
}

watch([maxBlocks, blocksPerRow], () => updateVisibleWindow())

const headerIndices = computed(() => {
  const n = Math.max(maxBlocks.value, blocksPerRow.value)
  return Array.from({ length: Math.min(n, blocksPerRow.value) }, (_, i) => i)
})

const rowAxisTicks = computed(() => {
  if (!data.value?.columns.length) return []
  const blocks = data.value.columns[0]?.blocks ?? []
  if (!blocks.length) return []
  const ticks: number[] = []
  const step = Math.max(1, Math.ceil(blocks.length / 8))
  for (let i = 0; i < blocks.length; i += step) {
    ticks.push(blocks[i].row_start)
  }
  const last = blocks[blocks.length - 1]
  if (ticks[ticks.length - 1] !== last.row_start) {
    ticks.push(last.row_start + last.row_count)
  }
  return ticks
})

const selectedBlockId = ref<number | null>(null)
const selectedColumn = ref<string | null>(null)

function onSelectBlock(column: string, block: StorageBlock) {
  selectedColumn.value = column
  selectedBlockId.value = block.block_id
  const prune = blockPruningMap.value[`${column}:${block.block_id}`]
  mapStore.selectBlock(column, block, prune)
  emit('selectBlock', { column, block })
}

function onKeydown(event: KeyboardEvent) {
  if (!data.value || selectedColumn.value == null || selectedBlockId.value == null) return
  const cols = data.value.columns
  const colIdx = cols.findIndex((c) => c.name === selectedColumn.value)
  if (colIdx < 0) return
  let nextCol = colIdx
  let nextBlock = selectedBlockId.value
  if (event.key === 'ArrowRight') nextBlock += 1
  else if (event.key === 'ArrowLeft') nextBlock -= 1
  else if (event.key === 'ArrowDown') nextCol = Math.min(cols.length - 1, colIdx + 1)
  else if (event.key === 'ArrowUp') nextCol = Math.max(0, colIdx - 1)
  else return
  event.preventDefault()
  const col = cols[nextCol]
  const maxId = col.blocks.length - 1
  nextBlock = Math.max(0, Math.min(maxId, nextBlock))
  const block = col.blocks.find((b) => b.block_id === nextBlock) ?? col.blocks[nextBlock]
  if (block) onSelectBlock(col.name, block)
}

onMounted(() => {
  if (props.datasetId) void mapStore.load(Number(props.datasetId))
  window.addEventListener('keydown', onKeydown)
  scrollRoot.value?.addEventListener('scroll', updateVisibleWindow, { passive: true })
  updateVisibleWindow()
})

watch(
  () => props.datasetId,
  (id) => {
    if (id) void mapStore.load(Number(id))
    else mapStore.clearSelection()
    updateVisibleWindow()
  },
)

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  scrollRoot.value?.removeEventListener('scroll', updateVisibleWindow)
})
</script>

<template>
  <section class="storage-map-canvas" tabindex="0">
    <div class="panel-header">
      <div class="header-left">
        <span class="panel-title">列块存储映射</span>
        <MapEncodingLegend />
      </div>
      <div class="header-tools">
        <label class="tool-item">
          <span>显示：</span>
          <select class="tool-select" disabled>
            <option>逻辑行范围</option>
          </select>
        </label>
        <label class="tool-item">
          <span>每行块数：</span>
          <select v-model.number="blocksPerRow" class="tool-select">
            <option :value="4">4</option>
            <option :value="6">6</option>
            <option :value="8">8</option>
            <option :value="12">12</option>
          </select>
        </label>
        <span v-if="data" class="tool-summary">{{ data.column_count }} 列 · {{ data.total_blocks }} 块</span>
      </div>
    </div>

    <div ref="scrollRoot" class="map-scroll">
      <p v-if="!datasetId" class="state-hint">选择数据集后显示列块映射</p>
      <p v-else-if="loading" class="state-hint">加载存储映射…</p>
      <p v-else-if="error" class="state-hint error">{{ error }}</p>
      <p v-else-if="!hasData" class="state-hint">暂无块数据，请先导入数据集</p>
      <div v-else-if="data" class="map-content">
        <div class="block-index-row" :style="{ paddingLeft: `${labelWidth + labelGap}px` }">
          <span
            v-for="idx in headerIndices"
            :key="idx"
            class="block-index mono"
            :style="{ width: `${cellWidth}px` }"
          >
            {{ formatBlockLabel(idx) }}
          </span>
        </div>
        <div class="map-grid">
          <ColumnTrack
            v-for="column in data.columns"
            :key="column.name"
            :name="column.name"
            :blocks="column.blocks"
            :blocks-per-row="blocksPerRow"
            :cell-width="cellWidth"
            :visible-start="visibleBlockStart"
            :visible-end="visibleBlockEnd"
            :selected-block-id="selectedColumn === column.name ? selectedBlockId : null"
            :active-block-id="
              activeScanBlock?.column === column.name
                ? activeScanBlock.block_id
                : selectedColumn === column.name
                  ? selectedBlockId
                  : null
            "
            :block-pruning-map="blockPruningMap"
            @select-block="(block) => onSelectBlock(column.name, block)"
          />
        </div>
        <div class="row-axis" :style="{ paddingLeft: `${labelWidth + labelGap}px` }">
          <span
            v-for="(tick, i) in rowAxisTicks"
            :key="i"
            class="row-tick mono"
          >
            {{ tick.toLocaleString() }}
          </span>
        </div>
      </div>
    </div>

    <p v-if="data" class="map-footer">
      {{ data.source }} · {{ data.row_count.toLocaleString() }} 行 · 方向键移动选中块
    </p>
  </section>
</template>

<style scoped>
.storage-map-canvas {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-raised);
  outline: none;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 10px;
  font-size: 12px;
  border-bottom: 1px solid var(--border-default);
  gap: 12px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.panel-title {
  font-weight: 600;
}

.header-tools {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--text-tertiary);
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tool-select {
  height: 24px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  font-size: 11px;
  color: var(--text-secondary);
  padding: 0 6px;
}

.tool-summary {
  white-space: nowrap;
}

.map-scroll {
  flex: 1;
  overflow: auto;
  min-height: 0;
  padding: 8px 12px 8px 10px;
}

.state-hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.state-hint.error {
  color: #b91c1c;
}

.map-content {
  min-width: max-content;
}

.block-index-row {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
  position: sticky;
  top: 0;
  background: var(--bg-raised);
  z-index: 2;
  padding-bottom: 4px;
}

.block-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.map-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.row-axis {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid var(--border-default);
  min-width: 200px;
}

.row-tick {
  font-size: 10px;
  color: var(--text-tertiary);
}

.map-footer {
  margin: 0;
  padding: 6px 10px;
  font-size: 11px;
  color: var(--text-tertiary);
  border-top: 1px solid var(--border-default);
  flex-shrink: 0;
}
</style>
