export type BlockWindowItem =
  | { kind: 'block'; index: number }
  | { kind: 'ellipsis' }

export type BlockWindowAlign = 'start' | 'end'

export type BlockWindowView = {
  items: BlockWindowItem[]
  align: BlockWindowAlign
}

export const BLOCK_CELL_WIDTH = 46
export const BLOCK_CELL_HEIGHT = 30
export const BLOCK_CELL_GAP = 3
export const TRACK_LABEL_WIDTH = 108
export const TRACK_ROW_HEIGHT = 40
export const ELLIPSIS_WIDTH = 20

/** 轨道块区左右内边距与标签列占用的总扣减（与 ColumnTrack / tracks-shell 一致）。 */
export const TRACK_BLOCKS_WIDTH_INSET = 4 + 4 + TRACK_LABEL_WIDTH + 6 + 8

const BLOCK_UNIT = BLOCK_CELL_WIDTH + BLOCK_CELL_GAP

/** 不含省略号时可放下的块数。 */
export function countBlocksThatFit(trackAreaWidth: number): number {
  if (trackAreaWidth <= 0) return 0
  return Math.floor((trackAreaWidth + BLOCK_CELL_GAP) / BLOCK_UNIT)
}

/** 含「… + 末块」窗口时最多可展示的块索引数。 */
export function capacityFromWidth(trackAreaWidth: number, totalBlocks: number): number {
  if (trackAreaWidth <= 0 || totalBlocks <= 0) return Math.max(totalBlocks, 9)
  const allFit = countBlocksThatFit(trackAreaWidth)
  if (allFit >= totalBlocks) return totalBlocks

  const headCount = Math.floor(
    (trackAreaWidth - ELLIPSIS_WIDTH - BLOCK_CELL_GAP - BLOCK_CELL_WIDTH + BLOCK_CELL_GAP) /
      BLOCK_UNIT,
  )
  return Math.max(4, headCount + 1)
}

export function buildBlockWindow(
  totalBlocks: number,
  maxVisibleBlocks: number,
  selectedIndex: number | null,
): BlockWindowView {
  if (totalBlocks <= 0) return { items: [], align: 'start' }
  if (totalBlocks <= maxVisibleBlocks) {
    return {
      items: Array.from({ length: totalBlocks }, (_, index) => ({ kind: 'block', index })),
      align: 'start',
    }
  }

  const last = totalBlocks - 1
  const leadingCount = maxVisibleBlocks - 1
  const tailSpan = maxVisibleBlocks - 2
  const tailStart = last - tailSpan + 1

  const defaultVisible = new Set<number>()
  for (let i = 0; i < leadingCount; i += 1) defaultVisible.add(i)
  defaultVisible.add(last)

  if (selectedIndex == null || defaultVisible.has(selectedIndex)) {
    const items: BlockWindowItem[] = []
    for (let i = 0; i < leadingCount; i += 1) items.push({ kind: 'block', index: i })
    items.push({ kind: 'ellipsis' })
    items.push({ kind: 'block', index: last })
    return { items, align: 'start' }
  }

  if (selectedIndex >= tailStart) {
    const items: BlockWindowItem[] = [{ kind: 'block', index: 0 }]
    items.push({ kind: 'ellipsis' })
    for (let i = tailStart; i <= last; i += 1) items.push({ kind: 'block', index: i })
    return { items, align: 'end' }
  }

  const items: BlockWindowItem[] = [{ kind: 'block', index: 0 }]
  const midStart = Math.max(1, selectedIndex - 1)
  const midEnd = Math.min(last - 1, selectedIndex + 1)

  if (midStart > 1) items.push({ kind: 'ellipsis' })
  for (let i = midStart; i <= midEnd; i += 1) items.push({ kind: 'block', index: i })
  if (midEnd < last - 1) items.push({ kind: 'ellipsis' })
  items.push({ kind: 'block', index: last })
  return { items, align: 'start' }
}

export function windowPixelWidth(items: BlockWindowItem[]): number {
  let width = 0
  for (const item of items) {
    if (item.kind === 'ellipsis') width += ELLIPSIS_WIDTH + BLOCK_CELL_GAP
    else width += BLOCK_CELL_WIDTH + BLOCK_CELL_GAP
  }
  return Math.max(0, width - BLOCK_CELL_GAP)
}
