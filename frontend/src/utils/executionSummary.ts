import { formatBytes } from '@/utils/format'

export type ExecutionMetricsLike = {
  block_accesses?: number
  scanned_blocks?: number
  cache_hits?: number
  compressed_operator_blocks?: number
  decoded_blocks?: number
  bytes_read?: number
  rows_output?: number
  pruned_blocks?: number
}

export function buildExecutionSummary(
  metrics: ExecutionMetricsLike | null | undefined,
  prunedBlocks?: number | null,
  totalBlocks?: number | null,
): string | null {
  if (!metrics) return null

  const total = totalBlocks ?? null
  const plannedPruned = prunedBlocks ?? null
  const accessed = metrics.block_accesses ?? 0
  const scanned = metrics.scanned_blocks ?? 0
  const cacheHits = metrics.cache_hits ?? 0
  const compressed = metrics.compressed_operator_blocks ?? 0
  const decoded = metrics.decoded_blocks ?? 0
  const rowsOut = metrics.rows_output ?? 0

  const parts: string[] = []

  if (total != null && total > 0 && plannedPruned != null) {
    const entered = Math.max(0, total - plannedPruned)
    parts.push(`${total} 个候选列块中，规划阶段提前排除 ${plannedPruned} 个，实际访问 ${accessed || entered} 个。`)
  } else if (accessed > 0) {
    parts.push(`实际访问 ${accessed} 个列块。`)
  }

  if (accessed > 0) {
    if (scanned === 0 && cacheHits > 0) {
      parts.push(`${cacheHits} 个块均命中缓存，没有磁盘读取。`)
    } else if (scanned > 0) {
      parts.push(`从磁盘读取 ${scanned} 个块。`)
    }
  }

  if (compressed > 0) {
    parts.push(`${compressed} 个块均在压缩结构上完成处理。`)
  }

  if (decoded === 0 && (compressed > 0 || accessed > 0)) {
    parts.push('没有完整解码。')
  } else if (decoded > 0) {
    parts.push(`${decoded} 个块进行了完整解码。`)
  }

  if (metrics.bytes_read != null && metrics.bytes_read > 0) {
    parts.push(`读取数据量 ${formatBytes(metrics.bytes_read)}`)
  }

  parts.push(`最终输出 ${rowsOut} 行结果`)

  if (!parts.length) return null
  return `${parts.join('；')}。`
}

export function buildBlockPruningStats(prunedBlocks: number, totalBlocks: number) {
  const entered = Math.max(0, totalBlocks - prunedBlocks)
  const rate = totalBlocks > 0 ? (prunedBlocks / totalBlocks) * 100 : 0
  return { totalBlocks, prunedBlocks, entered, rate }
}
