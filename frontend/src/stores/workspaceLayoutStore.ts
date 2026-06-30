import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'columnlab.workspace.layout'

type LayoutState = {
  leftWidth: number
  rightWidth: number
  /** @deprecated 旧版百分比，读取时迁移为 lowerHeightPx */
  lowerHeight?: number
  lowerHeightPx: number
  leftCollapsed: boolean
  rightCollapsed: boolean
  lowerCollapsed: boolean
}

const DEFAULT_LOWER_HEIGHT_PX = 160

const DEFAULT: LayoutState = {
  leftWidth: 196,
  rightWidth: 220,
  lowerHeightPx: DEFAULT_LOWER_HEIGHT_PX,
  leftCollapsed: false,
  rightCollapsed: false,
  lowerCollapsed: false,
}

function migrateLowerHeightPx(raw: Partial<LayoutState>): number {
  if (typeof raw.lowerHeightPx === 'number' && raw.lowerHeightPx > 0) {
    return raw.lowerHeightPx
  }
  if (typeof raw.lowerHeight === 'number' && raw.lowerHeight > 0) {
    const vh = typeof window !== 'undefined' ? window.innerHeight : 800
    return Math.round((vh * raw.lowerHeight) / 100)
  }
  return DEFAULT_LOWER_HEIGHT_PX
}

function loadState(): LayoutState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULT }
    const parsed = JSON.parse(raw) as Partial<LayoutState>
    return {
      ...DEFAULT,
      ...parsed,
      lowerHeightPx: migrateLowerHeightPx(parsed),
    }
  } catch {
    return { ...DEFAULT }
  }
}

export const useWorkspaceLayoutStore = defineStore('workspaceLayout', () => {
  const saved = loadState()
  const leftWidth = ref(saved.leftWidth)
  const rightWidth = ref(saved.rightWidth)
  const lowerHeightPx = ref(saved.lowerHeightPx)
  const leftCollapsed = ref(saved.leftCollapsed)
  const rightCollapsed = ref(saved.rightCollapsed)
  const lowerCollapsed = ref(saved.lowerCollapsed ?? false)

  function persist() {
    const state: LayoutState = {
      leftWidth: leftWidth.value,
      rightWidth: rightWidth.value,
      lowerHeightPx: lowerHeightPx.value,
      leftCollapsed: leftCollapsed.value,
      rightCollapsed: rightCollapsed.value,
      lowerCollapsed: lowerCollapsed.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }

  watch(
    [leftWidth, rightWidth, lowerHeightPx, leftCollapsed, rightCollapsed, lowerCollapsed],
    persist,
  )

  function clampLeftWidth(px: number, containerWidth: number) {
    const min = 140
    const max = Math.max(min, Math.round(containerWidth * 0.32))
    return Math.max(min, Math.min(max, px))
  }

  function clampRightWidth(px: number, containerWidth: number) {
    const min = 180
    const max = Math.max(min, Math.round(containerWidth * 0.38))
    return Math.max(min, Math.min(max, px))
  }

  function clampLowerHeight(px: number, containerHeight: number) {
    const min = 120
    const max = Math.max(min, Math.round(containerHeight * 0.55))
    return Math.max(min, Math.min(max, px))
  }

  function toggleLeft() {
    leftCollapsed.value = !leftCollapsed.value
  }

  function toggleRight() {
    rightCollapsed.value = !rightCollapsed.value
  }

  function toggleLower() {
    lowerCollapsed.value = !lowerCollapsed.value
  }

  return {
    leftWidth,
    rightWidth,
    lowerHeightPx,
    leftCollapsed,
    rightCollapsed,
    lowerCollapsed,
    clampLeftWidth,
    clampRightWidth,
    clampLowerHeight,
    toggleLeft,
    toggleRight,
    toggleLower,
  }
})
