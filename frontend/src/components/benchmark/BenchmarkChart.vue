<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  rows: Array<{ column: string; encoding: string; mean: number; p95: number }>
  title?: string
}>()

const svgRef = ref<SVGSVGElement | null>(null)

const chartData = computed(() => {
  const items = props.rows.filter((r) => r.column === 'qty')
  const maxVal = Math.max(...items.map((i) => i.mean), 1)
  return items.map((item, idx) => ({
    ...item,
    x: 40 + idx * 90,
    height: (item.mean / maxVal) * 140,
    label: item.encoding,
  }))
})

function exportPng() {
  const svg = svgRef.value
  if (!svg) return
  const serializer = new XMLSerializer()
  const source = serializer.serializeToString(svg)
  const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = 360
    canvas.height = 220
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0)
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
      <h2>{{ title ?? 'qty 列 encoded_bytes (mean)' }}</h2>
      <button type="button" class="export-btn" @click="exportPng">导出 PNG</button>
    </header>
    <svg ref="svgRef" viewBox="0 0 360 220" width="360" height="220" role="img" aria-label="benchmark chart">
      <line x1="30" y1="180" x2="330" y2="180" stroke="#ccc" stroke-width="1" />
      <g v-for="bar in chartData" :key="bar.encoding">
        <rect
          :x="bar.x"
          :y="180 - bar.height"
          width="48"
          :height="bar.height"
          fill="#6b7c93"
          rx="2"
        />
        <text :x="bar.x + 24" y="196" text-anchor="middle" font-size="10" fill="#666">
          {{ bar.label }}
        </text>
        <text :x="bar.x + 24" :y="170 - bar.height" text-anchor="middle" font-size="9" fill="#444">
          {{ Math.round(bar.mean) }}
        </text>
      </g>
    </svg>
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
</style>
