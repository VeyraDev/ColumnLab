<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useWorkspaceLayoutStore } from '@/stores/workspaceLayoutStore'
import { getDataset, listColumns, listTables, type ColumnSummary } from '@/api/datasets'
import { displayLogicalType } from '@/utils/format'

const props = defineProps<{
  datasetId?: string
}>()

const layoutStore = useWorkspaceLayoutStore()
const columns = ref<ColumnSummary[]>([])
const tableName = ref('')
const datasetName = ref('')
const loading = ref(false)

const totalBlocks = computed(() => columns.value.reduce((sum, col) => sum + col.block_count, 0))

const panelTitle = computed(() => {
  if (!datasetName.value) return '数据结构'
  return `${datasetName.value} (${columns.value.length} 列)`
})

async function loadStructure() {
  columns.value = []
  tableName.value = ''
  datasetName.value = ''
  if (!props.datasetId) return
  loading.value = true
  try {
    const ds = await getDataset(Number(props.datasetId))
    datasetName.value = ds.name
    const tables = await listTables(Number(props.datasetId))
    if (!tables.length) return
    tableName.value = tables[0].name
    columns.value = await listColumns(tables[0].id)
  } finally {
    loading.value = false
  }
}

onMounted(loadStructure)
watch(() => props.datasetId, loadStructure)
</script>

<template>
  <aside class="data-panel">
    <div class="panel-header">
      <span class="panel-title">{{ panelTitle }}</span>
      <button type="button" class="collapse-btn" title="折叠面板" @click="layoutStore.toggleLeft()">
        ‹
      </button>
    </div>
    <div class="panel-body">
      <p v-if="!datasetId" class="empty-hint">暂无列定义。导入数据后将在此显示表结构与块统计。</p>
      <p v-else-if="loading" class="empty-hint">加载中…</p>
      <p v-else-if="!columns.length" class="empty-hint">数据集尚未就绪或无表结构。</p>
      <template v-else>
        <table class="column-table">
          <thead>
            <tr>
              <th>列名</th>
              <th>类型</th>
              <th>块数</th>
              <th aria-hidden="true" />
            </tr>
          </thead>
          <tbody>
            <tr v-for="col in columns" :key="col.id">
              <td class="col-name mono">{{ col.name }}</td>
              <td class="col-type">{{ displayLogicalType(col.logical_type) }}</td>
              <td class="col-blocks mono">{{ col.block_count }}</td>
              <td class="col-chevron" aria-hidden="true">›</td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>
    <div class="panel-footer">
      <span class="mono">总计：{{ columns.length }} 列，{{ totalBlocks }} 块</span>
      <button type="button" class="refresh-btn" title="刷新" @click="loadStructure">↻</button>
    </div>
  </aside>
</template>

<style scoped>
.data-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-panel);
  border-right: 1px solid var(--border-default);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-raised);
}

.panel-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collapse-btn {
  width: 20px;
  height: 20px;
  padding: 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  font-size: 14px;
  line-height: 1;
  color: var(--text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
}

.panel-body {
  flex: 1;
  overflow: auto;
  padding: 0;
  min-height: 0;
}

.empty-hint {
  margin: 8px 10px;
  color: var(--text-tertiary);
  font-size: 12px;
  line-height: 1.5;
}

.column-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.column-table th {
  position: sticky;
  top: 0;
  background: var(--bg-muted);
  color: var(--text-tertiary);
  font-weight: 500;
  text-align: left;
  padding: 5px 8px;
  border-bottom: 1px solid var(--border-default);
}

.column-table td {
  padding: 5px 8px;
  border-bottom: 1px solid var(--border-subtle, var(--border-default));
  color: var(--text-secondary);
}

.col-name {
  color: var(--text-primary);
}

.col-blocks {
  text-align: right;
}

.col-chevron {
  width: 16px;
  color: var(--text-tertiary);
  text-align: center;
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  font-size: 11px;
  color: var(--text-tertiary);
  border-top: 1px solid var(--border-default);
}

.refresh-btn {
  width: 22px;
  height: 22px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  color: var(--text-secondary);
  cursor: pointer;
}
</style>
