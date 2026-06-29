import request from './request'

export interface DatasetSummary {
  id: number
  name: string
  description: string
  source_file_name: string
  source_sha256: string
  status: string
  active_version_id: number | null
  row_count: number
  table_count: number
  storage_path?: string | null
}

export interface TableSummary {
  id: number
  name: string
  row_count: number
  row_group_count: number
}

export interface ColumnSummary {
  id: number
  name: string
  logical_type: string
  scale: number
  nullable: boolean
  block_count: number
  raw_bytes: number
  encoded_bytes: number
}

export interface StorageBlock {
  block_id: number
  encoding: string
  row_start: number
  row_count: number
  compressed_bytes: number
  encoded_bytes: number
  raw_bytes: number
  null_count: number
  payload_crc32: string
}

export interface StorageMapColumn {
  name: string
  logical_type: string
  block_count: number
  blocks: StorageBlock[]
}

export interface StorageMap {
  source: string
  row_count: number
  column_count: number
  total_blocks: number
  columns: StorageMapColumn[]
}

export async function listDatasets() {
  const { data } = await request.get<{ data: DatasetSummary[] }>('/datasets')
  return data.data
}

export async function getDataset(id: number) {
  const { data } = await request.get<{ data: DatasetSummary }>(`/datasets/${id}`)
  return data.data
}

export async function listTables(datasetId: number) {
  const { data } = await request.get<{ data: TableSummary[] }>(`/datasets/${datasetId}/tables`)
  return data.data
}

export async function listColumns(tableId: number) {
  const { data } = await request.get<{ data: ColumnSummary[] }>(`/tables/${tableId}/columns`)
  return data.data
}

export async function getStorageMap(tableId: number) {
  const { data } = await request.get<{ data: StorageMap }>(`/tables/${tableId}/storage-map`)
  return data.data
}

export interface BlockPreviewCandidate {
  encoding: string
  encoded_bytes: number
  raw_bytes: number
  gain: number
  encode_ns: number
  selected: boolean
  reason: string
}

export interface BlockPreview {
  selection_reason: string
  winner_encoding: string
  candidates: BlockPreviewCandidate[]
  rle_runs?: Array<{ value: string | number; run_length: number; start: number }>
  dictionary?: {
    dictionary_count: number
    bit_width: number
    entries: string[]
    packed_codes_hex: string
    sample_codes: number[]
    row_count?: number
  }
  block?: {
    encoding: string
    row_start: number
    row_count: number
    crc32: string
  }
  column?: { id: number; name: string; logical_type: string }
  stats?: {
    null_count: number
    distinct_count: number
    min_repr: string | null
    max_repr: string | null
    raw_bytes: number
    encoded_bytes: number
  }
}

export interface BlockDetail {
  column_id: number
  column_name: string
  logical_type: string
  block_id: number
  row_start: number
  row_count: number
  encoding: string
  raw_bytes: number
  encoded_bytes: number
  compressed_bytes: number
  null_count: number
  distinct_count: number
  min_repr: string | null
  max_repr: string | null
  dictionary_count: number
  run_count: number
  payload_crc32: string
}

export async function getBlockDetail(columnId: number, blockId: number) {
  const { data } = await request.get<{ data: BlockDetail }>(
    `/columns/${columnId}/blocks/${blockId}`,
  )
  return data.data
}

export async function getBlockPreview(columnId: number, blockId: number) {
  const { data } = await request.get<{ data: BlockPreview }>(
    `/columns/${columnId}/blocks/${blockId}/preview`,
  )
  return data.data
}
