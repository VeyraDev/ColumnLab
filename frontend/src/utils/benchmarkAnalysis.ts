import type { BenchmarkConfig, MetricStats } from '@/api/benchmarks'
import {
  benchmarkMetricLabel,
  defaultAnalysisColumn,
  distributionLabels,
  encodingLabel,
} from '@/utils/terminology'
import { formatBytes } from '@/utils/format'

export type EncodingCompareRow = {
  encoding: string
  encodedBytes: number
  relativePercent: number
  savedPercent: number
}

export function resolveAnalysisColumn(config: BenchmarkConfig): string {
  const dist = config.distribution ?? 'run_length'
  return defaultAnalysisColumn[dist] ?? 'qty'
}

export function buildEncodingCompareRows(
  metrics: Record<string, MetricStats>,
  column: string,
): EncodingCompareRow[] {
  const encodings = ['RAW', 'RLE', 'DICTIONARY'] as const
  const rawKey = `${column}.RAW.encoded_bytes`
  const rawBytes = metrics[rawKey]?.mean ?? 0
  if (!rawBytes) return []

  return encodings.map((enc) => {
    const bytes = metrics[`${column}.${enc}.encoded_bytes`]?.mean ?? 0
    const relativePercent = rawBytes > 0 ? (bytes / rawBytes) * 100 : 0
    const savedPercent = Math.max(0, 100 - relativePercent)
    return {
      encoding: enc,
      encodedBytes: bytes,
      relativePercent,
      savedPercent,
    }
  })
}

export function pickBestEncoding(rows: EncodingCompareRow[]): EncodingCompareRow | null {
  if (!rows.length) return null
  return rows.reduce((best, row) => (row.encodedBytes < best.encodedBytes ? row : best))
}

export function buildCodecConclusion(
  config: BenchmarkConfig,
  metrics: Record<string, MetricStats>,
  column: string,
): { headline: string; detail: string; takeaway: string; meta: string[] } {
  const rows = buildEncodingCompareRows(metrics, column)
  const best = pickBestEncoding(rows)
  const raw = rows.find((r) => r.encoding === 'RAW')
  const distLabel = distributionLabels[config.distribution ?? 'run_length'] ?? config.distribution

  if (!best || !raw) {
    return {
      headline: '实验已完成',
      detail: '暂无足够数据生成结论。',
      takeaway: '',
      meta: [`测试数据：${distLabel}`, `分析列：${column}`],
    }
  }

  const bestName = best.encoding === 'RLE' ? 'RLE' : encodingLabel(best.encoding)
  let headline = `${distLabel}数据下，${column} 列 ${bestName} 编码体积最小。`
  if (best.encoding === 'RLE' && distLabel === '长游程') {
    headline = '长游程数据更适合 RLE。'
  }

  const detail =
    best.encoding === 'RAW'
      ? `${column} 列 RAW 为 ${formatBytes(raw.encodedBytes)}，三种方案体积接近。`
      : `在 ${column} 列中，${bestName} 的编码大小为 ${formatBytes(best.encodedBytes)}，` +
        `相比 RAW 的 ${formatBytes(raw.encodedBytes)} 减少约 ${best.savedPercent.toFixed(1)}%，` +
        `是当前三种方案中最小的。`

  const second = rows.filter((r) => r.encoding !== best.encoding && r.encoding !== 'RAW').sort((a, b) => a.encodedBytes - b.encodedBytes)[0]
  let takeaway = `结论：${distLabel}数据下 ${column} 列优先选择 ${bestName}。`
  if (second && second.encodedBytes > best.encodedBytes) {
    takeaway = `结论：${distLabel}数据优先选择 ${bestName}。`
  }

  const meta = [
    `测试数据：${distLabel}`,
    `分析列：${column}`,
    `行数：${config.row_count?.toLocaleString() ?? '—'}`,
    `随机种子：${config.seed ?? '—'}`,
  ]

  return { headline, detail, takeaway, meta }
}

export function metricTitle(metricKey: string, groupMode: 'encoding' | 'column'): string {
  const metricName = benchmarkMetricLabel(metricKey)
  const groupName = groupMode === 'encoding' ? '按编码比较' : '按列比较'
  return `${metricName} · ${groupName}`
}

export function formatMetricValue(metricKey: string, value: number): string {
  if (metricKey.includes('compression_ratio') || metricKey.includes('relative')) {
    return `${value.toFixed(1)}%`
  }
  if (metricKey.includes('_ns') || metricKey === 'query.execute_ns') {
    if (value < 1000) return `${Math.round(value)} ns`
    if (value < 1_000_000) return `${(value / 1000).toFixed(1)} µs`
    return `${(value / 1_000_000).toFixed(2)} ms`
  }
  if (metricKey.includes('encoded_bytes') || metricKey.includes('bytes')) {
    return formatBytes(value)
  }
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`
  if (value >= 1_000) return `${(value / 1000).toFixed(1)}K`
  return String(Math.round(value))
}
