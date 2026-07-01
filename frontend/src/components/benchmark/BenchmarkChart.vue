<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { encodingLabel } from '@/utils/terminology'
import { formatBytes } from '@/utils/format'

export interface ChartBar {
  key: string
  label: string
  value: number
  absoluteBytes?: number
  relativePercent?: number
}

const props = defineProps<{
  bars: ChartBar[]
  title?: string
  yLabel?: string
  relativeMode?: boolean
}>()

const EXPORT_WIDTH = 1600
const EXPORT_HEIGHT = 420
const CHART_HEIGHT = 300
const PAD = { top: 28, right: 16, bottom: 52, left: 56 }

const containerRef = ref<HTMLElement | null>(null)
const chartWidth = ref(640)
const svgRef = ref<SVGSVGElement | null>(null)

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  if (!containerRef.value) return
  resizeObserver = new ResizeObserver((entries) => {
    const w = entries[0]?.contentRect.width
    if (w && w > 0) chartWidth.value = w
  })
  resizeObserver.observe(containerRef.value)
  chartWidth.value = containerRef.value.clientWidth || 640
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

const innerWidth = computed(() => chartWidth.value - PAD.left - PAD.right)
const innerHeight = computed(() => CHART_HEIGHT - PAD.top - PAD.bottom)

const maxVal = computed(() => {
  if (props.relativeMode) return Math.max(100, ...props.bars.map((b) => b.relativePercent ?? b.value), 1)
  return Math.max(...props.bars.map((b) => b.value), 1)
})

const baselineY = computed(() => {
  if (!props.relativeMode) return null
  const y = PAD.top + innerHeight.value - (100 / maxVal.value) * innerHeight.value
  return y
})

const barLayout = computed(() => {
  const n = props.bars.length || 1
  const gap = 12
  const barW = Math.max(36, (innerWidth.value - gap * (n - 1)) / n)
  return props.bars.map((bar, idx) => {
    const val = props.relativeMode ? (bar.relativePercent ?? bar.value) : bar.value
    const h = (val / maxVal.value) * innerHeight.value
    return {
      ...bar,
      displayLabel: encodingLabel(bar.label),
      x: PAD.left + idx * (barW + gap),
      y: PAD.top + innerHeight.value - h,
      w: barW,
      h,
      val,
    }
  })
})

function valueLabel(bar: ChartBar & { val: number }): string {
  if (props.relativeMode) {
    const pct = `${(bar.relativePercent ?? bar.val).toFixed(1)}%`
    const bytes = bar.absoluteBytes != null ? formatBytes(bar.absoluteBytes) : ''
    return bytes ? `${pct}\n${bytes}` : pct
  }
  return String(Math.round(bar.val))
}

function exportPng() {
  const svg = svgRef.value
  if (!svg) return
  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute('width', String(EXPORT_WIDTH))
  clone.setAttribute('height', String(EXPORT_HEIGHT))
  clone.setAttribute('viewBox', `0 0 ${chartWidth.value} ${CHART_HEIGHT}`)
  const serializer = new XMLSerializer()
  const source = serializer.serializeToString(clone)
  const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = EXPORT_WIDTH
    canvas.height = EXPORT_HEIGHT
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, EXPORT_WIDTH, EXPORT_HEIGHT)
    canvas.toBlob((png) => {
      if (!png) return
      const a = document.createElement('a')
      a.href = URL.createObjectURL(png)
      a.download = 'benchmark-chart.png'
      a.click()
    })
    URL.revokeObjectURL(url)
  }
  img.src = url
}
</script>

<template>
  <section class="chart-panel">
    <header>
      <h2>{{ title ?? '实验指标' }}</h2>
      <button type="button" class="export-btn" @click="exportPng">导出 PNG</button>
    </header>
    <div ref="containerRef" class="chart-wrap">
      <svg
        ref="svgRef"
        :viewBox="`0 0 ${chartWidth} ${CHART_HEIGHT}`"
        :width="chartWidth"
        :height="CHART_HEIGHT"
        role="img"
        :aria-label="title ?? 'benchmark chart'"
      >
        <line
          :x1="PAD.left"
          :y1="PAD.top + innerHeight"
          :x2="chartWidth - PAD.right"
          :y2="PAD.top + innerHeight"
          stroke="#d1d5db"
          stroke-width="1"
        />
        <line
          v-if="relativeMode && baselineY != null"
          :x1="PAD.left"
          :y1="baselineY"
          :x2="chartWidth - PAD.right"
          :y2="baselineY"
          stroke="#9ca3af"
          stroke-width="1"
          stroke-dasharray="4 3"
        />
        <text
          v-if="relativeMode"
          :x="chartWidth - PAD.right"
          :y="(baselineY ?? 0) - 4"
          text-anchor="end"
          font-size="10"
          fill="#6b7280"
        >
          RAW 基准 100%
        </text>
        <g v-for="bar in barLayout" :key="bar.key">
          <rect :x="bar.x" :y="bar.y" :width="bar.w" :height="bar.h" fill="#6b7280" rx="2" />
          <text
            :x="bar.x + bar.w / 2"
            :y="PAD.top + innerHeight + 18"
            text-anchor="middle"
            font-size="11"
            fill="#374151"
          >
            {{ bar.displayLabel }}
          </text>
          <text
            :x="bar.x + bar.w / 2"
            :y="bar.y - 6"
            text-anchor="middle"
            font-size="10"
            fill="#374151"
          >
            {{ valueLabel(bar).split('\n')[0] }}
          </text>
          <text
            v-if="valueLabel(bar).includes('\n')"
            :x="bar.x + bar.w / 2"
            :y="bar.y - 18"
            text-anchor="middle"
            font-size="9"
            fill="#6b7280"
          >
            {{ valueLabel(bar).split('\n')[1] }}
          </text>
        </g>
        <text
          :x="14"
          :y="PAD.top + innerHeight / 2"
          font-size="10"
          fill="#9ca3af"
          transform-origin="14 center"
          transform="rotate(-90 14 90)"
        >
          {{ yLabel ?? 'value' }}
        </text>
      </svg>
    </div>
  </section>
</template>

<style scoped>
.chart-panel {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 10px 12px;
  background: var(--bg-panel);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}

.export-btn {
  font-size: 11px;
  padding: 4px 8px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-muted);
  cursor: pointer;
}

.chart-wrap {
  min-height: 300px;
  width: 100%;
}
</style>
