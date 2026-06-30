export type BlockWindowItem =
  | { kind: 'block'; index: number }
  | { kind: 'ellipsis' }

export const BLOCK_CELL_WIDTH = 40
export const BLOCK_CELL_HEIGHT = 26
export const BLOCK_CELL_GAP = 3
export const TRACK_LABEL_WIDTH = 88
export const ELLIPSIS_WIDTH = 20

/** 不含省略号时可放下的块数。 */
export function countBlocksThatFit(trackAreaWidth: number): number {
  if (trackAreaWidth <= 0) return 0
  const unit = BLOCK_CELL_WIDTH + BLOCK_CELL_GAP
  return Math.floor((trackAreaWidth + BLOCK_CELL_GAP) / unit)
}

/**
 * 根据轨道可用宽度计算可见块数（含末块）。
 * 宽屏显示更多块；全部能放下时不使用省略号。
 */
export function capacityFromWidth(trackAreaWidth: number, totalBlocks: number): number {
  if (trackAreaWidth <= 0 || totalBlocks <= 0) return Math.max(totalBlocks, 7)
  const allFit = countBlocksThatFit(trackAreaWidth)
  if (allFit >= totalBlocks) return totalBlocks

  const unit = BLOCK_CELL_WIDTH + BLOCK_CELL_GAP
  const headCount = Math.floor(
    (trackAreaWidth - ELLIPSIS_WIDTH - BLOCK_CELL_GAP - BLOCK_CELL_WIDTH + BLOCK_CELL_GAP) / unit,
  )
  return Math.max(3, headCount + 1)
}

export function buildBlockWindow(
  totalBlocks: number,
  maxBlocks: number,
  selectedIndex: number | null,
): BlockWindowItem[] {
  if (totalBlocks <= 0) return []
  if (totalBlocks <= maxBlocks) {
    return Array.from({ length: totalBlocks }, (_, index) => ({ kind: 'block', index }))
  }

  const last = totalBlocks - 1
  const headCount = maxBlocks - 1
  const defaultVisible = new Set<number>()
  for (let i = 0; i < headCount; i += 1) defaultVisible.add(i)
  defaultVisible.add(last)

  if (selectedIndex == null || defaultVisible.has(selectedIndex)) {
    const items: BlockWindowItem[] = []
    for (let i = 0; i < headCount; i += 1) items.push({ kind: 'block', index: i })
    items.push({ kind: 'ellipsis' })
    items.push({ kind: 'block', index: last })
    return items
  }

  const items: BlockWindowItem[] = []
  items.push({ kind: 'block', index: 0 })

  const midStart = Math.max(1, selectedIndex - 1)
  const midEnd = Math.min(last - 1, selectedIndex + 1)

  if (midStart > 1) items.push({ kind: 'ellipsis' })
  for (let i = midStart; i <= midEnd; i += 1) {
    items.push({ kind: 'block', index: i })
  }
  if (midEnd < last - 1) items.push({ kind: 'ellipsis' })
  items.push({ kind: 'block', index: last })
  return items
}

/** 估算窗口占用宽度，用于空白检测。 */
export function windowPixelWidth(items: BlockWindowItem[]): number {
  let width = 0
  for (const item of items) {
    if (item.kind === 'ellipsis') width += ELLIPSIS_WIDTH + BLOCK_CELL_GAP
    else width += BLOCK_CELL_WIDTH + BLOCK_CELL_GAP
  }
  return Math.max(0, width - BLOCK_CELL_GAP)
}
