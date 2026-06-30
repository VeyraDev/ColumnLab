<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import ColumnTrack, { type StorageBlock } from './ColumnTrack.vue'
import MapEncodingLegend from '@/components/workspace/MapEncodingLegend.vue'
import { useStorageMapStore } from '@/stores/storageMapStore'
import { useStorageMapViewStore } from '@/stores/storageMapViewStore'
import {
  BLOCK_CELL_WIDTH,
  TRACK_BLOCKS_WIDTH_INSET,
  TRACK_ROW_HEIGHT,
  buildBlockWindow,
  capacityFromWidth,
} from './blockWindow'
import type { BlockPruningState } from '@/api/queries'

const TRACK_GAP = 0

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
const { visibleBlockDensity } = storeToRefs(viewStore)

const blockPruningMap = computed(() => {
  const map: Record<string, { state: string; reason: string }> = {}
  for (const entry of props.blockPruning ?? []) {
    map[`${entry.column}:${entry.block_id}`] = { state: entry.state, reason: entry.reason }
  }
  return map
})

const scrollRoot = ref<HTMLElement | null>(null)
const trackAreaWidth = ref(480)
const visibleColumnStart = ref(0)
const visibleColumnEnd = ref(32)

const data = computed(() => mapData.value)

const maxBlocks = computed(() =>
  Math.max(...(data.value?.columns.map((col) => col.blocks.length) ?? [0]), 0),
)

const effectiveCapacity = computed(() => {
  const auto = capacityFromWidth(trackAreaWidth.value, maxBlocks.value)
  if (visibleBlockDensity.value === 0) return auto
  return Math.min(visibleBlockDensity.value, auto)
})

const blockWindowView = computed(() =>
  buildBlockWindow(maxBlocks.value, effectiveCapacity.value, selectedBlockId.value),
)

const blockWindow = computed(() => blockWindowView.value.items)
const blockWindowAlign = computed(() => blockWindowView.value.align)

const axisBlocks = computed(() => {
  if (!data.value?.columns.length) return []
  return data.value.columns[0]?.blocks ?? []
})

function axisTickLabel(index: number): string {
  const block = axisBlocks.value[index]
  if (!block) return ''
  return block.row_start.toLocaleString()
}

const selectedBlockId = ref<number | null>(null)
const selectedColumn = ref<string | null>(null)

const visibleColumns = computed(() => {
  if (!data.value) return []
  const start = Math.max(0, visibleColumnStart.value)
  const end = Math.min(data.value.columns.length, visibleColumnEnd.value + 1)
  return data.value.columns.slice(start, end)
})

function updateVisibleWindow() {
  const el = scrollRoot.value
  if (!el || !data.value) return
  const start = Math.max(0, Math.floor(el.scrollTop / (TRACK_ROW_HEIGHT + TRACK_GAP)) - 2)
  const visibleCount = Math.ceil(el.clientHeight / (TRACK_ROW_HEIGHT + TRACK_GAP)) + 4
  visibleColumnStart.value = start
  visibleColumnEnd.value = Math.min(data.value.columns.length - 1, start + visibleCount)
}

function updateTrackAreaWidth() {
  const el = scrollRoot.value
  if (!el) return
  trackAreaWidth.value = Math.max(0, el.clientWidth - TRACK_BLOCKS_WIDTH_INSET)
}

let resizeObserver: ResizeObserver | null = null

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
  if (scrollRoot.value) {
    resizeObserver = new ResizeObserver(updateTrackAreaWidth)
    resizeObserver.observe(scrollRoot.value)
    updateTrackAreaWidth()
  }
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

watch(maxBlocks, updateVisibleWindow)

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  scrollRoot.value?.removeEventListener('scroll', updateVisibleWindow)
  resizeObserver?.disconnect()
})
</script>

<template>
  <section class="storage-map-canvas workspace-panel" tabindex="0">
    <div class="panel-header">
      <span class="panel-title">列块存储映射</span>
      <MapEncodingLegend class="header-legend" />
      <div class="header-tools">
        <label class="tool-item">
          <span class="tool-label">显示</span>
          <select class="tool-select" disabled>
            <option>逻辑行范围</option>
          </select>
        </label>
        <label class="tool-item">
          <span class="tool-label">密度</span>
          <select v-model.number="visibleBlockDensity" class="tool-select">
            <option :value="0">自动</option>
            <option :value="7">7</option>
            <option :value="9">9</option>
            <option :value="11">11</option>
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
        <div class="tracks-shell">
          <div class="map-grid">
            <ColumnTrack
              v-for="(column, colIdx) in visibleColumns"
              :key="column.name"
              :name="column.name"
              :logical-type="column.logical_type"
              :blocks="column.blocks"
              :block-window="blockWindow"
              :block-window-align="blockWindowAlign"
              :is-last="colIdx === visibleColumns.length - 1"
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
          <div class="row-axis">
            <span class="axis-title">逻辑行号</span>
            <div class="axis-track" :class="{ 'align-end': blockWindowAlign === 'end' }">
              <template v-for="(item, idx) in blockWindow" :key="`axis-${item.kind}-${idx}`">
                <span
                  v-if="item.kind === 'ellipsis'"
                  class="axis-ellipsis"
                  aria-hidden="true"
                />
                <span v-else class="axis-tick mono" :title="`块 ${item.index + 1}`">
                  {{ axisTickLabel(item.index) }}
                </span>
              </template>
            </div>
          </div>
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
  outline: none;
}

.panel-header {
  display: flex;
  align-items: center;
  height: var(--workspace-panel-header-height);
  min-height: var(--workspace-panel-header-height);
  padding: 0 12px;
  font-size: 13px;
  border-bottom: 1px solid var(--border-subtle);
  gap: 12px;
  flex-shrink: 0;
  flex-wrap: nowrap;
  overflow: hidden;
  background: var(--bg-raised);
}

.panel-title {
  font-weight: 600;
  color: var(--text-primary);
  flex-shrink: 0;
  white-space: nowrap;
}

.header-legend {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.header-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.tool-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tool-label {
  color: var(--text-secondary);
}

.tool-select {
  height: 26px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  font-size: 12px;
  color: var(--text-primary);
  padding: 0 8px;
}

.tool-summary {
  white-space: nowrap;
  color: var(--text-secondary);
}

.map-scroll {
  flex: 1;
  overflow: auto;
  min-height: 0;
  padding: 2px 0 4px;
}

.state-hint {
  margin: 0;
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-muted);
}

.state-hint.error {
  color: var(--danger);
}

.map-content {
  display: flex;
  flex-direction: column;
  min-height: 0;
  width: 100%;
}

.tracks-shell {
  width: 100%;
  min-width: 0;
  padding: 0 4px;
}

.map-grid {
  display: flex;
  flex-direction: column;
  min-width: 0;
  width: 100%;
}

.row-axis {
  display: grid;
  grid-template-columns: 108px minmax(0, 1fr);
  gap: 6px;
  align-items: end;
  margin-top: 4px;
  padding: 4px 8px 0 4px;
  border-top: 1px solid var(--border-subtle);
}

.axis-title {
  font-size: 10px;
  color: var(--text-muted);
  text-align: right;
  padding-right: 2px;
  white-space: nowrap;
}

.axis-track {
  display: flex;
  flex-wrap: nowrap;
  align-items: flex-end;
  gap: 3px;
  min-width: 0;
}

.axis-tick {
  flex-shrink: 0;
  width: 46px;
  font-size: 10px;
  color: var(--text-secondary);
  text-align: center;
  border-top: 1px solid var(--border-strong);
  padding-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.axis-ellipsis {
  flex-shrink: 0;
  width: 20px;
  height: 1px;
  border-top: 1px dashed var(--border-default);
  margin-bottom: 4px;
}

.axis-track.align-end {
  margin-left: auto;
}

.map-footer {
  margin: 0;
  padding: 2px 8px;
  font-size: 11px;
  color: var(--text-muted);
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

@media (max-width: 900px) {
  .tool-label {
    display: none;
  }
}
</style>
