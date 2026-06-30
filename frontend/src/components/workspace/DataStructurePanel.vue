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
const loading = ref(false)

const totalBlocks = computed(() => columns.value.reduce((sum, col) => sum + col.block_count, 0))

async function loadStructure() {
  columns.value = []
  tableName.value = ''
  if (!props.datasetId) return
  loading.value = true
  try {
    const ds = await getDataset(Number(props.datasetId))
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
  <aside class="data-panel workspace-panel">
    <div class="panel-header">
      <span class="panel-title">数据结构</span>
      <button type="button" class="collapse-btn" title="折叠面板" @click="layoutStore.toggleLeft()">
        ‹
      </button>
    </div>
    <div class="panel-body">
      <p v-if="!datasetId" class="empty-hint">暂无列定义。导入数据后将在此显示表结构与块统计。</p>
      <p v-else-if="loading" class="empty-hint">加载中…</p>
      <p v-else-if="!columns.length" class="empty-hint">数据集尚未就绪或无表结构。</p>
      <template v-else>
        <div class="object-header">
          <span class="object-name">{{ tableName }}</span>
          <span class="object-meta">{{ columns.length }} 列</span>
        </div>
        <div class="table-wrap">
          <table class="column-table">
            <thead>
              <tr>
                <th>列名</th>
                <th>类型</th>
                <th class="th-count">块数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="col in columns" :key="col.id">
                <td class="col-name mono" :title="col.name">{{ col.name }}</td>
                <td class="col-type">{{ displayLogicalType(col.logical_type) }}</td>
                <td class="col-blocks mono">{{ col.block_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
    <div v-if="columns.length" class="panel-footer">
      <span class="mono">总计 {{ totalBlocks }} 块</span>
      <button type="button" class="refresh-btn" title="刷新" @click="loadStructure">↻</button>
    </div>
  </aside>
</template>

<style scoped>
.data-panel {
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: var(--workspace-panel-header-height);
  min-height: var(--workspace-panel-header-height);
  padding: 0 12px;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-raised);
}

.collapse-btn {
  width: 26px;
  height: 26px;
  padding: 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  font-size: 16px;
  line-height: 1;
  color: var(--text-secondary);
  cursor: pointer;
}

.panel-body {
  flex: 1;
  overflow: auto;
  overflow-x: hidden;
  padding: 8px;
  min-height: 0;
  min-width: 0;
}

.empty-hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.object-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  height: 36px;
  padding: 0 10px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--border-subtle);
}

.object-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.object-meta {
  font-size: 12px;
  color: var(--text-secondary);
}

.table-wrap {
  padding: 0 2px;
}

.column-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}

.column-table th {
  height: 32px;
  background: var(--bg-muted);
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 12px;
  text-align: left;
  padding: 0 10px;
  border-bottom: 1px solid var(--border-default);
}

.column-table th.th-count {
  width: 48px;
  text-align: right;
}

.column-table th:nth-child(2) {
  width: 92px;
}

.column-table td {
  height: 34px;
  padding: 0 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
}

.column-table tbody tr:hover {
  background: var(--bg-muted);
}

.col-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-type {
  white-space: nowrap;
  color: var(--text-body);
}

.col-blocks {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-subtle);
}

.refresh-btn {
  width: 26px;
  height: 26px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  color: var(--text-secondary);
  cursor: pointer;
}
</style>
