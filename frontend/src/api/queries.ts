import request from './request'



export interface QueryError {

  code: string

  message: string

  line: number | null

  col: number | null

}



export interface LogicalPlanNode {

  type: string

  label: string

  details: Record<string, unknown>

  children: LogicalPlanNode[]

}



export interface OptimizerTraceEntry {

  rule: string

  changed: boolean

  detail: string

}



export interface BlockPruningState {

  column: string

  block_id: number

  state: string

  verdict: string

  reason: string

}



export interface OperatorMetric {

  operator_id: string

  operator_type: string

  input_rows: number

  output_rows: number

  elapsed_ns: number

}



export interface QueryMetrics {

  scanned_blocks: number

  pruned_blocks: number

  cache_hits: number

  bytes_read: number

  rows_examined: number

  rows_output: number

  compressed_operator_blocks: number

  decoded_blocks: number

  block_accesses?: number

  peak_memory: number

  execute_time?: number

  operators: OperatorMetric[]

}



export interface QuerySubmitResult {

  query_id: number

  status: string

  error: QueryError | null

  plan_summary: string | null

  total_blocks: number

  pruned_blocks: number

}



export interface QueryExplain {

  query_id: number

  status: string

  sql_text: string

  logical_plan: Record<string, unknown> | null

  plan_tree: LogicalPlanNode | null

  optimized_plan: Record<string, unknown> | null

  optimized_plan_tree: LogicalPlanNode | null

  physical_plan: Record<string, unknown> | null

  physical_plan_tree: LogicalPlanNode | null

  optimizer_trace: OptimizerTraceEntry[]

  block_pruning: BlockPruningState[]

  metrics: QueryMetrics | null

  total_blocks: number

  pruned_blocks: number

  error: QueryError | null

}



export interface QueryResult {

  query_id: number

  status: string

  columns: string[]

  rows: unknown[][]

  total_rows: number

  offset: number

  limit: number

}



export interface QueryHistoryItem {

  id: number

  sql_text: string

  status: string

  created_at: string

}



export async function submitQuery(payload: {

  dataset_id: number

  sql: string

  table_id?: number

}) {

  const { data } = await request.post<{ data: QuerySubmitResult }>('/queries', payload)

  return data.data

}



export async function fetchExplain(queryId: number) {

  const { data } = await request.get<{ data: QueryExplain }>(`/queries/${queryId}/explain`)

  return data.data

}



export async function fetchQueryHistory(datasetId: number, limit = 20) {

  const { data } = await request.get<{ data: QueryHistoryItem[] }>('/queries', {

    params: { dataset_id: datasetId, limit },

  })

  return data.data

}



export async function fetchQueryStatus(queryId: number) {
  const { data } = await request.get<{
    data: { status: string; metrics?: QueryMetrics | null }
  }>(`/queries/${queryId}`)
  return data.data
}



export async function fetchQueryResult(queryId: number, offset = 0, limit = 200) {

  const { data } = await request.get<{ data: QueryResult }>(`/queries/${queryId}/result`, {

    params: { offset, limit },

  })

  return data.data

}



export async function cancelQuery(queryId: number) {

  const { data } = await request.post<{ data: { query_id: number; status: string } }>(

    `/queries/${queryId}/cancel`,

  )

  return data.data

}



export function pruningKey(column: string, blockId: number) {

  return `${column}:${blockId}`

}

