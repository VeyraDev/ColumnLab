import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getStorageMap, listColumns, listTables, type StorageMap } from '@/api/datasets'
import type { StorageBlock } from '@/api/datasets'

export type SelectedBlockMeta = {
  column: string
  column_id: number
  block_id: number
  encoding: string
  row_start: number
  row_count: number
  compressed_bytes: number
  encoded_bytes: number
  raw_bytes: number
  payload_crc32: string
  prune_state?: string
  prune_reason?: string
}

export const useStorageMapStore = defineStore('storageMap', () => {
  const mapData = ref<StorageMap | null>(null)
  const columnIds = ref<Record<string, number>>({})
  const tableId = ref<number | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedBlock = ref<SelectedBlockMeta | null>(null)

  const hasData = computed(() => mapData.value !== null && mapData.value.columns.length > 0)

  async function load(datasetId: number) {
    loading.value = true
    error.value = null
    mapData.value = null
    columnIds.value = {}
    tableId.value = null
    selectedBlock.value = null
    try {
      const tables = await listTables(datasetId)
      if (!tables.length) {
        error.value = '数据集尚无表'
        return
      }
      tableId.value = tables[0].id
      const cols = await listColumns(tables[0].id)
      columnIds.value = Object.fromEntries(cols.map((c) => [c.name, c.id]))
      mapData.value = await getStorageMap(tables[0].id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载存储映射失败'
    } finally {
      loading.value = false
    }
  }

  function selectBlock(
    column: string,
    block: StorageBlock,
    prune?: { state?: string; reason?: string },
  ) {
    const columnId = columnIds.value[column]
    if (columnId == null) return
    selectedBlock.value = {
      column,
      column_id: columnId,
      block_id: block.block_id,
      encoding: block.encoding,
      row_start: block.row_start,
      row_count: block.row_count,
      compressed_bytes: block.compressed_bytes,
      encoded_bytes: block.encoded_bytes,
      raw_bytes: block.raw_bytes,
      payload_crc32: block.payload_crc32,
      prune_state: prune?.state,
      prune_reason: prune?.reason,
    }
  }

  function clearSelection() {
    selectedBlock.value = null
  }

  return {
    mapData,
    columnIds,
    tableId,
    loading,
    error,
    selectedBlock,
    hasData,
    load,
    selectBlock,
    clearSelection,
  }
})
