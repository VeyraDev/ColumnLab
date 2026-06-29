import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  cancelQuery,
  fetchExplain,
  fetchQueryHistory,
  fetchQueryResult,
  fetchQueryStatus,
  pruningKey,
  submitQuery,
  type BlockPruningState,
  type LogicalPlanNode,
  type OperatorMetric,
  type OptimizerTraceEntry,
  type QueryError,
  type QueryHistoryItem,
  type QueryMetrics,
} from '@/api/queries'

const TEMPLATE_SQL = 'SELECT id FROM data LIMIT 10'

export const useQueryStore = defineStore('query', () => {
  const sqlText = ref(TEMPLATE_SQL)
  const tableId = ref<number | undefined>()
  const loading = ref(false)
  const currentQueryId = ref<number | null>(null)
  const status = ref<string | null>(null)
  const error = ref<QueryError | null>(null)
  const planSummary = ref<string | null>(null)
  const planTree = ref<LogicalPlanNode | null>(null)
  const optimizedPlanTree = ref<LogicalPlanNode | null>(null)
  const physicalPlanTree = ref<LogicalPlanNode | null>(null)
  const optimizerTrace = ref<OptimizerTraceEntry[]>([])
  const blockPruning = ref<BlockPruningState[]>([])
  const metrics = ref<QueryMetrics | null>(null)
  const operatorMetrics = ref<OperatorMetric[]>([])
  const resultColumns = ref<string[]>([])
  const resultRows = ref<unknown[][]>([])
  const totalResultRows = ref(0)
  const activeScanBlock = ref<{ column: string; block_id: number } | null>(null)
  const totalBlocks = ref(0)
  const prunedBlocks = ref(0)
  const history = ref<QueryHistoryItem[]>([])
  const pollCancelled = ref(false)

  const hasError = computed(() => error.value !== null)
  const isRunning = computed(() => status.value === 'running')

  const blockPruningMap = computed(() => {
    const map: Record<string, BlockPruningState> = {}
    for (const entry of blockPruning.value) {
      map[pruningKey(entry.column, entry.block_id)] = entry
    }
    return map
  })

  function summarizePlan(plan: Record<string, unknown>): string {
    const types: string[] = []
    let node: Record<string, unknown> | null = plan
    while (node) {
      types.push(String(node.type ?? '?'))
      node = (node.child as Record<string, unknown> | undefined) ?? null
    }
    return types.join(' → ')
  }

  function applyExplain(explain: Awaited<ReturnType<typeof fetchExplain>>) {
    error.value = explain.error
    status.value = explain.status
    planTree.value = explain.plan_tree
    optimizedPlanTree.value = explain.optimized_plan_tree
    physicalPlanTree.value = explain.physical_plan_tree
    optimizerTrace.value = explain.optimizer_trace
    blockPruning.value = explain.block_pruning
    metrics.value = explain.metrics
    operatorMetrics.value = explain.metrics?.operators ?? []
    totalBlocks.value = explain.total_blocks
    prunedBlocks.value = explain.pruned_blocks
    planSummary.value = explain.physical_plan
      ? summarizePlan(explain.physical_plan)
      : explain.optimized_plan
        ? summarizePlan(explain.optimized_plan)
        : explain.plan_tree?.type ?? null
  }

  function applySchemaDefault(tableName: string, columnName: string, resolvedTableId: number) {
    tableId.value = resolvedTableId
    if (sqlText.value === TEMPLATE_SQL || !sqlText.value.trim()) {
      sqlText.value = `SELECT ${columnName} FROM ${tableName} LIMIT 10`
    }
  }

  async function pollUntilDone(queryId: number) {
    pollCancelled.value = false
    for (let i = 0; i < 100; i++) {
      if (pollCancelled.value) return 'cancelled'
      const st = await fetchQueryStatus(queryId)
      status.value = st.status
      const m = (st as { metrics?: QueryMetrics }).metrics
      if (m) {
        metrics.value = m
        operatorMetrics.value = m.operators ?? []
      }
      if (st.status === 'completed' || st.status === 'failed' || st.status === 'cancelled') {
        return st.status
      }
      await new Promise((r) => setTimeout(r, 300))
    }
    return status.value
  }

  async function cancelRunningQuery() {
    if (!currentQueryId.value || !isRunning.value) return
    pollCancelled.value = true
    await cancelQuery(currentQueryId.value)
    status.value = 'cancelled'
    loading.value = false
  }

  async function loadResult(queryId: number) {
    try {
      const result = await fetchQueryResult(queryId)
      resultColumns.value = result.columns
      resultRows.value = result.rows
      totalResultRows.value = result.total_rows
      status.value = result.status
    } catch {
      resultColumns.value = []
      resultRows.value = []
    }
  }

  async function runQuery(datasetId: number, overrideTableId?: number) {
    if (!datasetId || !sqlText.value.trim()) return
    loading.value = true
    error.value = null
    planTree.value = null
    optimizedPlanTree.value = null
    physicalPlanTree.value = null
    optimizerTrace.value = []
    blockPruning.value = []
    metrics.value = null
    operatorMetrics.value = []
    resultColumns.value = []
    resultRows.value = []
    planSummary.value = null
    activeScanBlock.value = null
    try {
      const result = await submitQuery({
        dataset_id: datasetId,
        sql: sqlText.value,
        table_id: overrideTableId ?? tableId.value,
      })
      currentQueryId.value = result.query_id
      status.value = result.status
      totalBlocks.value = result.total_blocks
      prunedBlocks.value = result.pruned_blocks
      if (result.error) {
        error.value = result.error
        planSummary.value = result.plan_summary
      } else if (result.query_id) {
        applyExplain(await fetchExplain(result.query_id))
        const finalStatus = await pollUntilDone(result.query_id)
        applyExplain(await fetchExplain(result.query_id))
        if (finalStatus === 'completed') {
          await loadResult(result.query_id)
        }
      }
      await refreshHistory(datasetId)
    } finally {
      loading.value = false
      activeScanBlock.value = null
    }
  }

  async function refreshHistory(datasetId: number) {
    history.value = await fetchQueryHistory(datasetId)
  }

  async function loadFromHistory(item: QueryHistoryItem) {
    sqlText.value = item.sql_text
    currentQueryId.value = item.id
    status.value = item.status
    await fetchExplain(item.id).then(applyExplain)
    if (item.status === 'completed') {
      await loadResult(item.id)
    }
  }

  function getPruning(column: string, blockId: number): BlockPruningState | undefined {
    return blockPruningMap.value[pruningKey(column, blockId)]
  }

  return {
    sqlText,
    tableId,
    applySchemaDefault,
    loading,
    currentQueryId,
    status,
    error,
    planSummary,
    planTree,
    optimizedPlanTree,
    physicalPlanTree,
    optimizerTrace,
    blockPruning,
    blockPruningMap,
    metrics,
    operatorMetrics,
    resultColumns,
    resultRows,
    totalResultRows,
    activeScanBlock,
    totalBlocks,
    prunedBlocks,
    history,
    hasError,
    isRunning,
    runQuery,
    cancelRunningQuery,
    refreshHistory,
    loadFromHistory,
    getPruning,
  }
})
