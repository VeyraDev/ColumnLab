export const operatorLabels: Record<string, string> = {
  BlockScan: '读取列块',
  RleFilter: 'RLE 压缩过滤',
  DictionaryFilter: '字典编码过滤',
  RawFilter: '普通数据过滤',
  BitmapAnd: '多条件求交',
  BitmapOr: '多条件求并',
  HashAggregate: '分组聚合',
  Aggregate: '分组聚合',
  Materialize: '生成查询结果',
  Sort: '结果排序',
  Limit: '限制结果数量',
  Project: '列投影',
  Scan: '读取表',
  Filter: '筛选',
}

export const optimizerLabels: Record<string, string> = {
  constant_folding: '预计算常量条件',
  predicate_normalization: '规范化筛选条件',
  projection_pruning: '仅读取必要列',
  predicate_pushdown: '提前执行筛选',
  aggregate_pushdown: '尝试提前聚合',
  limit_pushdown: '提前限制结果数量',
}

export const optimizerStatusLabels = {
  applied: '已应用',
  unchanged: '未变化',
  notApplicable: '不适用',
} as const

export const profileMetricLabels: Record<string, string> = {
  block_accesses: '实际访问块',
  scanned_blocks: '磁盘读取块',
  cache_hits: '缓存命中块',
  compressed_operator_blocks: '压缩态处理块',
  decoded_blocks: '完整解码块',
  rows_output: '结果行数',
  bytes_read: '读取数据量',
}

export const benchmarkKindLabels = {
  codec: '编码效果实验',
  query: '查询执行实验',
} as const

export const benchmarkMetricLabels: Record<string, string> = {
  encoded_bytes: '编码后存储大小',
  compression_ratio: '空间节省率',
  encode_ns: '编码耗时',
  decode_ns: '解码耗时',
  filter_eq_ns: '等值过滤耗时',
  filter_range_ns: '范围过滤耗时',
  aggregate_sum_ns: 'SUM聚合耗时',
  peak_memory_bytes: '峰值内存',
  'query.execute_ns': '查询执行时间',
  scanned_blocks: '磁盘读取块数',
  block_accesses: '实际访问块数',
  bytes_read: '实际读取数据量',
  decoded_blocks: '完整解码块数',
  cache_hits: '缓存命中块数',
}

export const encodingDisplayLabels: Record<string, string> = {
  RAW: 'RAW',
  RLE: 'RLE',
  DICTIONARY: 'Dictionary',
  DICT: 'Dictionary',
}

export const distributionLabels: Record<string, string> = {
  run_length: '长游程',
  low_cardinality: '低基数',
  high_cardinality: '高基数',
  uniform: '均匀',
  skewed: '偏斜',
  with_null: '含 NULL',
  mixed_business: '混合业务',
}

export const defaultAnalysisColumn: Record<string, string> = {
  run_length: 'qty',
  low_cardinality: 'region',
  high_cardinality: 'region',
  uniform: 'qty',
  skewed: 'qty',
  with_null: 'region',
  mixed_business: 'qty',
}

export const codecSelectionReasonLabels: Record<string, string> = {
  smallest_encoded_bytes: '编码后体积最小',
  gain_below_min_gain: '空间收益低于阈值，保留 RAW',
  tie_break_decode_cost: '候选大小接近，选择解码成本较低的方案',
}

const STORAGE_METRICS = new Set(['encoded_bytes', 'compression_ratio', 'peak_memory_bytes'])
const TIMING_METRICS = new Set([
  'encode_ns',
  'decode_ns',
  'filter_eq_ns',
  'filter_range_ns',
  'aggregate_sum_ns',
  'query.execute_ns',
])

export function operatorLabel(type: string): string {
  return operatorLabels[type] ?? type
}

export function optimizerLabel(rule: string): string {
  return optimizerLabels[rule] ?? rule
}

export function benchmarkMetricLabel(key: string): string {
  return benchmarkMetricLabels[key] ?? key
}

export function encodingLabel(encoding: string): string {
  return encodingDisplayLabels[encoding.toUpperCase()] ?? encoding
}

export function codecReasonLabel(reason: string): string {
  return codecSelectionReasonLabels[reason] ?? reason
}

export function isStorageBenchmarkMetric(metric: string): boolean {
  return STORAGE_METRICS.has(metric) || metric.endsWith('.encoded_bytes') || metric.endsWith('.compression_ratio')
}

export function isTimingBenchmarkMetric(metric: string): boolean {
  return TIMING_METRICS.has(metric) || metric.endsWith('_ns')
}

export function optimizerSummarySentence(appliedRules: string[]): string {
  if (!appliedRules.length) {
    return '当前查询结构已经较简单，优化器未改变逻辑步骤。'
  }
  const labels = appliedRules.map((r) => `「${optimizerLabel(r)}」`).join('、')
  if (appliedRules.includes('projection_pruning')) {
    return `本次查询应用了${labels}，执行时只打开查询涉及的列文件。`
  }
  return `本次查询应用了${labels}。`
}

export function formatPlanNodeLabel(node: {
  type: string
  details: Record<string, unknown>
}): { primary: string; secondary?: string } {
  const type = node.type
  const d = node.details
  const secondary = type

  switch (type) {
    case 'Scan': {
      const table = String(d.table ?? 'data')
      const ann = d.annotations as Record<string, unknown> | undefined
      const req = ann?.required_columns
      let primary = `读取表 ${table}`
      if (Array.isArray(req) && req.length) {
        primary += `\n需要列：${req.join('、')}`
      }
      return { primary, secondary }
    }
    case 'BlockScan': {
      const col = String(d.column ?? '—')
      return { primary: `读取 ${col} 列块`, secondary }
    }
    case 'Limit':
      return {
        primary: `限制结果数量 limit=${d.limit ?? 0} offset=${d.offset ?? 0}`,
        secondary,
      }
    case 'HashAggregate':
    case 'Aggregate':
      return { primary: operatorLabel('HashAggregate'), secondary }
    default:
      return { primary: operatorLabel(type), secondary: type !== operatorLabel(type) ? type : undefined }
  }
}
