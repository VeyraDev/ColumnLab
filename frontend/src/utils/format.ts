export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MiB`
}

export function formatGiB(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '—'
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GiB`
}

export function formatDurationMs(seconds?: number | null): string {
  if (seconds == null || !Number.isFinite(seconds)) return '—'
  return `${(seconds * 1000).toFixed(1)} ms`
}

export function formatBlockLabel(blockId: number): string {
  return String(blockId + 1).padStart(2, '0')
}

const TYPE_DISPLAY: Record<string, string> = {
  INT64: 'BIGINT',
  INT32: 'INT',
  UTF8: 'VARCHAR',
  FLOAT64: 'DOUBLE',
  FLOAT32: 'FLOAT',
  BOOLEAN: 'BOOLEAN',
  DECIMAL: 'DECIMAL',
  DATE: 'DATE',
  TIMESTAMP: 'TIMESTAMP',
}

export function displayLogicalType(logicalType: string): string {
  const key = logicalType.toUpperCase()
  return TYPE_DISPLAY[key] ?? key
}

export function encodingShortLabel(encoding: string): string {
  const upper = encoding.toUpperCase()
  if (upper === 'DICTIONARY' || upper === 'DICT') return 'DICT'
  if (upper === 'RLE') return 'RLE'
  if (upper === 'RAW') return 'RAW'
  return upper.slice(0, 4)
}
