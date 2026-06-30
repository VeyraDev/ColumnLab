import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'columnlab.workspace.layout'
const LAYOUT_VERSION = 4

const PANEL_GAP = 6
const CENTER_MIN_RATIO = 0.6

const MIN_LEFT_WIDTH = 220
const MIN_RIGHT_WIDTH = 260
const MIN_LOWER_HEIGHT_PX = 190

type LayoutState = {
  version: number
  leftWidth: number
  rightWidth: number
  lowerHeight?: number
  lowerHeightPx: number
  leftCollapsed: boolean
  rightCollapsed: boolean
  lowerCollapsed: boolean
}

const DEFAULT: LayoutState = {
  version: LAYOUT_VERSION,
  leftWidth: MIN_LEFT_WIDTH,
  rightWidth: MIN_RIGHT_WIDTH,
  lowerHeightPx: MIN_LOWER_HEIGHT_PX,
  leftCollapsed: false,
  rightCollapsed: false,
  lowerCollapsed: false,
}

const LEGACY_V1_LEFT = new Set([140, 196, 200])
const LEGACY_V1_RIGHT = new Set([180, 220, 280])
const LEGACY_V2_LEFT = new Set([300])
const LEGACY_V2_RIGHT = new Set([340])
const LEGACY_V3_LEFT = new Set([260])
const LEGACY_V3_RIGHT = new Set([300])
const LEGACY_LOWER = new Set([120, 156, 160, 210, 220])

function migrateLowerHeightPx(raw: Partial<LayoutState>): number {
  if (typeof raw.lowerHeightPx === 'number' && raw.lowerHeightPx > 0) {
    return raw.lowerHeightPx
  }
  if (typeof raw.lowerHeight === 'number' && raw.lowerHeight > 0) {
    const vh = typeof window !== 'undefined' ? window.innerHeight : 952
    return Math.round((vh * raw.lowerHeight) / 100)
  }
  return MIN_LOWER_HEIGHT_PX
}

function shouldResetToCurrentDefaults(parsed: Partial<LayoutState>): boolean {
  const version = parsed.version ?? 0
  if (version >= LAYOUT_VERSION) return false
  const left = parsed.leftWidth
  const right = parsed.rightWidth
  const lower = migrateLowerHeightPx(parsed)
  const leftLegacy =
    left == null ||
    LEGACY_V1_LEFT.has(left) ||
    LEGACY_V2_LEFT.has(left) ||
    LEGACY_V3_LEFT.has(left)
  const rightLegacy =
    right == null ||
    LEGACY_V1_RIGHT.has(right) ||
    LEGACY_V2_RIGHT.has(right) ||
    LEGACY_V3_RIGHT.has(right)
  const lowerLegacy = LEGACY_LOWER.has(lower)
  return leftLegacy && rightLegacy && lowerLegacy
}

function loadState(): LayoutState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULT }
    const parsed = JSON.parse(raw) as Partial<LayoutState>
    if (shouldResetToCurrentDefaults(parsed)) {
      return {
        ...DEFAULT,
        leftCollapsed: parsed.leftCollapsed ?? false,
        rightCollapsed: parsed.rightCollapsed ?? false,
        lowerCollapsed: parsed.lowerCollapsed ?? false,
      }
    }
    return {
      ...DEFAULT,
      ...parsed,
      version: LAYOUT_VERSION,
      lowerHeightPx: migrateLowerHeightPx(parsed),
    }
  } catch {
    return { ...DEFAULT }
  }
}

function sideGaps(leftCollapsed: boolean, rightCollapsed: boolean): number {
  let gaps = 0
  if (!leftCollapsed) gaps += PANEL_GAP
  if (!rightCollapsed) gaps += PANEL_GAP
  return gaps
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
      version: LAYOUT_VERSION,
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

  function maxSideWidth(containerWidth: number, leftCollapsed: boolean, rightCollapsed: boolean) {
    const gaps = sideGaps(leftCollapsed, rightCollapsed)
    const minCenter = Math.ceil(containerWidth * CENTER_MIN_RATIO)
    return Math.max(0, containerWidth - gaps - minCenter)
  }

  function clampLeftWidth(
    px: number,
    containerWidth: number,
    rightPx = rightWidth.value,
    isLeftCollapsed = leftCollapsed.value,
    isRightCollapsed = rightCollapsed.value,
  ) {
    const min = MIN_LEFT_WIDTH
    const maxCombined = maxSideWidth(containerWidth, isLeftCollapsed, isRightCollapsed)
    const max = Math.max(min, maxCombined - (isRightCollapsed ? 0 : Math.max(MIN_RIGHT_WIDTH, rightPx)))
    return Math.max(min, Math.min(max, px))
  }

  function clampRightWidth(
    px: number,
    containerWidth: number,
    leftPx = leftWidth.value,
    isLeftCollapsed = leftCollapsed.value,
    isRightCollapsed = rightCollapsed.value,
  ) {
    const min = MIN_RIGHT_WIDTH
    const maxCombined = maxSideWidth(containerWidth, isLeftCollapsed, isRightCollapsed)
    const max = Math.max(min, maxCombined - (isLeftCollapsed ? 0 : Math.max(MIN_LEFT_WIDTH, leftPx)))
    return Math.max(min, Math.min(max, px))
  }

  function clampLowerHeight(px: number, containerHeight: number) {
    const min = MIN_LOWER_HEIGHT_PX
    const max = Math.min(280, Math.max(min, Math.round(containerHeight * 0.42)))
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
