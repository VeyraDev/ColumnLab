<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { Database, FlaskConical, SearchCode, Settings, Upload, ChevronDown, ChevronUp } from 'lucide-vue-next'
import { usePanelResize } from '@/composables/usePanelResize'
import { useQueryStore } from '@/stores/query'
import { useStorageMapStore } from '@/stores/storageMapStore'
import { useWorkspaceLayoutStore } from '@/stores/workspaceLayoutStore'
import FunctionRail from '@/components/workspace/FunctionRail.vue'
import TopBar from '@/components/workspace/TopBar.vue'
import DataStructurePanel from '@/components/workspace/DataStructurePanel.vue'
import StatusBar from '@/components/workspace/StatusBar.vue'
import PanelSplitter from '@/components/workspace/PanelSplitter.vue'
import StorageMapCanvas from '@/components/storage-map/StorageMapCanvas.vue'
import BlockInspector from '@/components/block-inspector/BlockInspector.vue'
import ExecutionWorkbench from '@/components/execution-plan/ExecutionWorkbench.vue'
import type { StorageBlock } from '@/components/storage-map/ColumnTrack.vue'

const props = defineProps<{
  datasetId?: string
}>()

const router = useRouter()
const queryStore = useQueryStore()
const mapStore = useStorageMapStore()
const layoutStore = useWorkspaceLayoutStore()
const { startHorizontalResize, startVerticalResize } = usePanelResize()

const { blockPruning, activeScanBlock } = storeToRefs(queryStore)
const { selectedBlock } = storeToRefs(mapStore)
const { leftWidth, rightWidth, lowerHeightPx, leftCollapsed, rightCollapsed, lowerCollapsed } =
  storeToRefs(layoutStore)

const activeRail = ref('map')
const workspaceMainRef = ref<HTMLElement | null>(null)
const isResizing = ref(false)

function onRailClick(id: string) {
  activeRail.value = id
  if (id === 'import') router.push('/imports')
  if (id === 'lab' && props.datasetId) router.push(`/compression-lab/${props.datasetId}`)
  if (id === 'query' && props.datasetId) router.push(`/query/${props.datasetId}`)
}

function onSelectBlock(payload: { column: string; block: StorageBlock }) {
  const pruning = queryStore.getPruning(payload.column, payload.block.block_id)
  mapStore.selectBlock(payload.column, payload.block, {
    state: pruning?.state,
    reason: pruning?.reason,
  })
}

const railItems = [
  { id: 'import', icon: Upload, label: '数据导入', title: '数据导入' },
  { id: 'map', icon: Database, label: '存储映射', title: '存储映射' },
  { id: 'query', icon: SearchCode, label: '查询执行', title: '查询执行' },
  { id: 'lab', icon: FlaskConical, label: '压缩实验', title: '压缩实验' },
]

function containerWidth() {
  return workspaceMainRef.value?.clientWidth ?? window.innerWidth
}

function mainHeight() {
  return workspaceMainRef.value?.clientHeight ?? window.innerHeight
}

function beginResize() {
  isResizing.value = true
}

function endResize() {
  isResizing.value = false
}

function onResizeLeft(event: PointerEvent) {
  if (leftCollapsed.value) return
  beginResize()
  startHorizontalResize({
    event,
    startSize: leftWidth.value,
    min: 220,
    max: layoutStore.clampLeftWidth(9999, containerWidth()),
    captureTarget: event.currentTarget as HTMLElement,
    onEnd: endResize,
    onMove: (size) => {
      leftWidth.value = layoutStore.clampLeftWidth(size, containerWidth(), rightWidth.value)
    },
  })
}

function onResizeRight(event: PointerEvent) {
  if (rightCollapsed.value) return
  beginResize()
  startHorizontalResize({
    event,
    startSize: rightWidth.value,
    min: 260,
    max: layoutStore.clampRightWidth(9999, containerWidth()),
    invert: true,
    captureTarget: event.currentTarget as HTMLElement,
    onEnd: endResize,
    onMove: (size) => {
      rightWidth.value = layoutStore.clampRightWidth(size, containerWidth(), leftWidth.value)
    },
  })
}

function onResizeLower(event: PointerEvent) {
  if (lowerCollapsed.value) return
  beginResize()
  startVerticalResize({
    event,
    startSize: lowerHeightPx.value,
    min: 190,
    max: layoutStore.clampLowerHeight(9999, mainHeight()),
    captureTarget: event.currentTarget as HTMLElement,
    onEnd: endResize,
    onMove: (size) => {
      lowerHeightPx.value = layoutStore.clampLowerHeight(size, mainHeight())
    },
  })
}

const lowerGridRows = () => {
  if (lowerCollapsed.value) return 'minmax(0, 1fr) auto'
  return `minmax(0, 1fr) auto ${lowerHeightPx.value}px`
}
</script>

<template>
  <div class="workspace-shell">
    <TopBar :dataset-id="props.datasetId" />
    <div class="workspace-body">
      <nav class="function-rail" aria-label="功能轨道">
        <FunctionRail
          v-for="item in railItems"
          :key="item.id"
          :icon="item.icon"
          :label="item.label"
          :title="item.title"
          :active="activeRail === item.id"
          @click="onRailClick(item.id)"
        />
        <FunctionRail
          label="设置"
          title="设置"
          class="rail-settings"
          :icon="Settings"
          :active="activeRail === 'settings'"
          @click="activeRail = 'settings'"
        />
      </nav>

      <div
        ref="workspaceMainRef"
        class="workspace-main"
        :class="{ 'is-resizing': isResizing }"
        :style="{ gridTemplateRows: lowerGridRows() }"
      >
        <div class="upper-row">
          <button
            v-if="leftCollapsed"
            type="button"
            class="edge-expand left"
            title="展开数据结构"
            @click="layoutStore.toggleLeft()"
          >
            ›
          </button>

          <aside
            v-show="!leftCollapsed"
            class="side-panel"
            :style="{ width: `${leftWidth}px` }"
          >
            <DataStructurePanel :dataset-id="props.datasetId" />
          </aside>

          <PanelSplitter
            v-if="!leftCollapsed"
            orientation="vertical"
            class="splitter-left"
            :style="{ left: `${leftWidth}px` }"
            title="拖拽调整数据结构宽度"
            @resize-start="onResizeLeft"
          />

          <div class="center-panel">
            <StorageMapCanvas
              :dataset-id="props.datasetId"
              :block-pruning="blockPruning"
              :active-scan-block="activeScanBlock"
              @select-block="onSelectBlock"
            />
          </div>

          <PanelSplitter
            v-if="!rightCollapsed"
            orientation="vertical"
            class="splitter-right"
            :style="{ right: `${rightWidth}px` }"
            title="拖拽调整块检查器宽度"
            @resize-start="onResizeRight"
          />

          <aside
            v-show="!rightCollapsed"
            class="side-panel"
            :style="{ width: `${rightWidth}px` }"
          >
            <BlockInspector :selected-block="selectedBlock" />
          </aside>

          <button
            v-if="rightCollapsed"
            type="button"
            class="edge-expand right"
            title="展开块检查器"
            @click="layoutStore.toggleRight()"
          >
            ‹
          </button>
        </div>

        <div class="lower-splitter-bar">
          <PanelSplitter
            v-if="!lowerCollapsed"
            orientation="horizontal"
            class="lower-splitter"
            title="拖拽调整执行轨迹高度"
            @resize-start="onResizeLower"
          />
          <button
            type="button"
            class="lower-toggle"
            :title="lowerCollapsed ? '展开执行区' : '收起执行区'"
            @click="layoutStore.toggleLower()"
          >
            <ChevronDown v-if="!lowerCollapsed" :size="12" :stroke-width="2" />
            <ChevronUp v-else :size="12" :stroke-width="2" />
          </button>
        </div>

        <div v-show="!lowerCollapsed" class="lower-row">
          <ExecutionWorkbench />
        </div>
      </div>
    </div>
    <StatusBar :dataset-id="props.datasetId" />
  </div>
</template>

<style scoped>
.workspace-shell {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-app);
}

.workspace-body {
  display: grid;
  grid-template-columns: var(--workspace-rail-width) minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
  padding: 4px 4px 0 0;
  gap: var(--workspace-panel-gap);
  background: var(--bg-app);
}

.function-rail {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 1px;
  padding: 4px 0;
  background: transparent;
}

.rail-settings {
  margin-top: auto;
}

.workspace-main {
  display: grid;
  min-height: 0;
  overflow: hidden;
  padding: 0 4px 4px 0;
  gap: 0;
  background: transparent;
}

.workspace-main.is-resizing .upper-row,
.workspace-main.is-resizing .lower-row {
  pointer-events: none;
}

.upper-row {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: var(--workspace-panel-gap);
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.side-panel {
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.center-panel {
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
}

.splitter-left,
.splitter-right {
  transform: translateX(calc(var(--workspace-panel-gap) / 2));
}

.splitter-right {
  transform: translateX(calc(var(--workspace-panel-gap) / -2));
}

.lower-splitter-bar {
  position: relative;
  flex-shrink: 0;
  height: 6px;
  margin: 0;
  background: transparent;
}

.lower-splitter-bar :deep(.panel-splitter.horizontal) {
  height: 8px;
  margin: 0;
}

.lower-toggle {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 21;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 14px;
  padding: 0;
  border: 1px solid var(--border-default);
  border-radius: 2px;
  background: var(--bg-panel);
  color: var(--text-secondary);
  cursor: pointer;
}

.lower-toggle:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.lower-row {
  min-height: 0;
  overflow: hidden;
}

.edge-expand {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 5;
  width: 14px;
  height: 40px;
  border: 1px solid var(--border-default);
  background: var(--bg-panel);
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
}

.edge-expand.left {
  left: 0;
}

.edge-expand.right {
  right: 0;
}
</style>

<style>
body.is-resizing-col {
  cursor: col-resize !important;
  user-select: none;
}

body.is-resizing-row {
  cursor: row-resize !important;
  user-select: none;
}
</style>
