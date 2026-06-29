<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  columns: string[]
  rows: unknown[][]
  totalRows?: number
}>()

const scrollRoot = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const rowHeight = 22
const overscan = 8

const displayTotal = computed(() => props.totalRows ?? props.rows.length)
const totalHeight = computed(() => props.rows.length * rowHeight)

const visibleRange = computed(() => {
  const viewH = scrollRoot.value?.clientHeight ?? rowHeight * 12
  const start = Math.max(0, Math.floor(scrollTop.value / rowHeight) - overscan)
  const visibleCount = Math.ceil(viewH / rowHeight) + overscan * 2
  const end = Math.min(props.rows.length, start + visibleCount)
  return { start, end }
})

const visibleRows = computed(() =>
  props.rows.slice(visibleRange.value.start, visibleRange.value.end),
)

const paddingTop = computed(() => visibleRange.value.start * rowHeight)
const paddingBottom = computed(() =>
  Math.max(0, totalHeight.value - paddingTop.value - visibleRows.value.length * rowHeight),
)

function onScroll() {
  if (scrollRoot.value) scrollTop.value = scrollRoot.value.scrollTop
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return 'NULL'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return String(value)
}
</script>

<template>
  <section class="result-grid">
    <div class="grid-header">
      <span class="grid-title">查询结果</span>
      <span class="grid-count">{{ displayTotal }} 行</span>
    </div>
    <div v-if="columns.length" ref="scrollRoot" class="grid-scroll" @scroll="onScroll">
      <table class="grid-table">
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="paddingTop" :style="{ height: `${paddingTop}px` }" aria-hidden="true">
            <td :colspan="columns.length" />
          </tr>
          <tr
            v-for="(row, ri) in visibleRows"
            :key="visibleRange.start + ri"
            :style="{ height: `${rowHeight}px` }"
          >
            <td v-for="(col, ci) in columns" :key="col">{{ formatCell(row[ci]) }}</td>
          </tr>
          <tr v-if="paddingBottom" :style="{ height: `${paddingBottom}px` }" aria-hidden="true">
            <td :colspan="columns.length" />
          </tr>
        </tbody>
      </table>
    </div>
    <p v-else class="grid-empty">执行完成后在此显示结果</p>
  </section>
</template>

<style scoped>
.result-grid {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
  background: var(--bg-panel);
}

.grid-header {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
}

.grid-count {
  font-weight: 400;
  color: var(--text-tertiary);
}

.grid-scroll {
  flex: 1;
  overflow: auto;
  min-height: 0;
  max-height: 280px;
}

.grid-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.grid-table th,
.grid-table td {
  padding: 3px 8px;
  text-align: left;
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
}

.grid-table th {
  position: sticky;
  top: 0;
  background: var(--bg-muted);
  font-weight: 600;
  z-index: 1;
}

.grid-empty {
  margin: 0;
  padding: 10px;
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
