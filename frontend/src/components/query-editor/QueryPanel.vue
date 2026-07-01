<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { listColumns, listTables } from '@/api/datasets'
import { useQueryStore } from '@/stores/query'
import QueryEditor from '@/components/query-editor/QueryEditor.vue'
import QueryHistory from '@/components/query-editor/QueryHistory.vue'
import SqlBuilder from '@/components/query-editor/SqlBuilder.vue'
import OptimizedPlanTree from '@/components/execution-plan/OptimizedPlanTree.vue'
import PhysicalPlanTree from '@/components/execution-plan/PhysicalPlanTree.vue'
import OperatorMetrics from '@/components/query-editor/OperatorMetrics.vue'
import ResultGrid from '@/components/query-editor/ResultGrid.vue'
import ExecutionTrace from '@/components/execution-plan/ExecutionTrace.vue'

const props = defineProps<{
  datasetId?: string
}>()

type TabId = 'sql' | 'plan' | 'result' | 'profile' | 'history'

const activeTab = ref<TabId>('sql')
const queryStore = useQueryStore()
const {
  sqlText,
  loading,
  error,
  status,
  isRunning,
  planTree,
  optimizedPlanTree,
  physicalPlanTree,
  optimizerTrace,
  planSummary,
  history,
  prunedBlocks,
  totalBlocks,
  metrics,
  operatorMetrics,
  resultColumns,
  resultRows,
  totalResultRows,
} = storeToRefs(queryStore)

const tableName = ref('data')
const schemaColumns = ref<Array<{ name: string; logical_type: string }>>([])

async function loadSchema(id: number) {
  try {
    const tables = await listTables(id)
    if (!tables.length) return
    tableName.value = tables[0].name
    const cols = await listColumns(tables[0].id)
    schemaColumns.value = cols.map((c) => ({ name: c.name, logical_type: c.logical_type }))
    if (cols.length) {
      queryStore.applySchemaDefault(tables[0].name, cols[0].name, tables[0].id)
    }
  } catch {
    schemaColumns.value = []
  }
}

async function runQuery() {
  const id = Number(props.datasetId)
  if (!id) return
  await queryStore.runQuery(id)
  if (activeTab.value === 'sql') activeTab.value = 'result'
}

async function cancelQueryRun() {
  await queryStore.cancelRunningQuery()
}

function onSelectHistory(item: { id: number; sql_text: string; status: string }) {
  queryStore.loadFromHistory(item)
  activeTab.value = 'sql'
}

function onBuilderInsert(snippet: string) {
  sqlText.value = snippet
}

watch(
  () => props.datasetId,
  (id) => {
    if (!id) return
    const numericId = Number(id)
    void queryStore.refreshHistory(numericId)
    void loadSchema(numericId)
  },
  { immediate: true },
)

onMounted(() => {
  if (props.datasetId) {
    void queryStore.refreshHistory(Number(props.datasetId))
    void loadSchema(Number(props.datasetId))
  }
})

defineExpose({ runQuery })
</script>

<template>
  <div class="query-panel">
    <QueryHistory :items="history" @select="onSelectHistory" />
    <div class="query-main">
      <nav class="tab-bar">
        <button
          v-for="tab in [
            { id: 'sql', label: 'SQL' },
            { id: 'plan', label: '计划' },
            { id: 'result', label: '结果' },
            { id: 'profile', label: 'Profile' },
            { id: 'history', label: '历史' },
          ]"
          :key="tab.id"
          type="button"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id as TabId"
        >
          {{ tab.label }}
        </button>
      </nav>

      <div v-show="activeTab === 'sql'" class="tab-panel sql-tab">
        <SqlBuilder
          :table-name="tableName"
          :columns="schemaColumns"
          @insert="onBuilderInsert"
        />
        <QueryEditor
          v-model="sqlText"
          :error="error"
          :loading="loading"
          :running="isRunning"
          @run="runQuery"
          @cancel="cancelQueryRun"
        />
      </div>

      <div v-show="activeTab === 'plan'" class="tab-panel plan-tab">
        <OptimizedPlanTree
          :logical-node="planTree"
          :optimized-node="optimizedPlanTree"
          :trace="optimizerTrace"
          :summary="planSummary"
          :pruned-blocks="prunedBlocks"
          :total-blocks="totalBlocks"
        />
        <PhysicalPlanTree :node="physicalPlanTree" />
      </div>

      <div v-show="activeTab === 'result'" class="tab-panel result-tab">
        <ResultGrid
          :columns="resultColumns"
          :rows="resultRows"
          :total-rows="totalResultRows"
        />
      </div>

      <div v-show="activeTab === 'profile'" class="tab-panel profile-tab">
        <OperatorMetrics
          :metrics="metrics"
          :operators="operatorMetrics"
          :status="status"
          :pruned-blocks="prunedBlocks"
          :total-blocks="totalBlocks"
        />
        <ExecutionTrace
          :status="status"
          :physical-plan-tree="physicalPlanTree"
          :metrics="metrics"
          :operators="operatorMetrics"
          :pruned-blocks="prunedBlocks"
          :total-blocks="totalBlocks"
        />
      </div>

      <div v-show="activeTab === 'history'" class="tab-panel history-tab">
        <p class="hint">左侧列表可快速切换历史查询；选中后切回 SQL 或结果 Tab 查看详情。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.query-panel {
  display: grid;
  grid-template-columns: minmax(140px, 200px) minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  border-top: 1px solid var(--border-default);
  overflow: hidden;
}

.query-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--bg-muted);
}

.tab-panel {
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.result-tab,
.plan-tab,
.profile-tab,
.history-tab {
  flex: 1;
}

.sql-tab {
  flex: 0 1 auto;
  justify-content: flex-start;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-default);
}

.sql-tab .query-editor {
  flex: 0 0 auto;
}

.plan-tab {
  flex-direction: row;
  background: var(--bg-panel);
}

.tab-bar {
  display: flex;
  gap: 2px;
  padding: 4px 8px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-muted);
  flex-shrink: 0;
}

.tab-bar button {
  height: 24px;
  padding: 0 10px;
  border: 1px solid transparent;
  background: transparent;
  font-size: 11px;
  cursor: pointer;
  color: var(--text-secondary);
}

.tab-bar button.active {
  background: var(--bg-panel);
  border-color: var(--border-default);
  color: var(--text-primary);
}

.history-tab .hint {
  margin: 10px;
  font-size: 12px;
  color: var(--text-tertiary);
}

@media (max-width: 1366px) {
  .plan-tab {
    flex-direction: column;
  }
}
</style>
