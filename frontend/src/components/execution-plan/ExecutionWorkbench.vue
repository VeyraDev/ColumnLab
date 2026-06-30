<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useQueryStore } from '@/stores/query'
import LogicalPlanTreeNode from '@/components/execution-plan/LogicalPlanTreeNode.vue'
import { formatBytes, formatDurationMs } from '@/utils/format'

const queryStore = useQueryStore()
const {
  status,
  isRunning,
  sqlText,
  physicalPlanTree,
  metrics,
  history,
  currentQueryId,
} = storeToRefs(queryStore)

const summary = computed(() => {
  const m = metrics.value
  if (!m) return null
  const total = m.scanned_blocks + m.pruned_blocks
  const scannedPct = total > 0 ? ((m.scanned_blocks / total) * 100).toFixed(1) : '0.0'
  return {
    scanned: m.scanned_blocks,
    pruned: m.pruned_blocks,
    scannedPct,
    prunedPct: total > 0 ? ((m.pruned_blocks / total) * 100).toFixed(1) : '0.0',
    decoded: m.decoded_blocks,
    bytesRead: m.bytes_read,
    rowsOut: m.rows_output,
    totalTime: (m as { total_time?: number }).total_time ?? m.execute_time,
  }
})

const filterText = computed(() => {
  const sql = sqlText.value.trim()
  if (!sql) return null
  const match = sql.match(/\bwhere\b([\s\S]*?)(?:\bgroup\b|\border\b|\blimit\b|$)/i)
  if (match?.[1]?.trim()) return `WHERE ${match[1].trim()}`
  const groupMatch = sql.match(/\bgroup\s+by\b([\s\S]*?)(?:\border\b|\blimit\b|$)/i)
  if (groupMatch?.[1]?.trim()) return `GROUP BY ${groupMatch[1].trim()}`
  return sql.length > 80 ? `${sql.slice(0, 80)}…` : sql
})

const runMeta = computed(() => {
  const item = history.value[0]
  return { createdAt: item?.created_at ?? null }
})

const statusLabel = computed(() => {
  if (isRunning.value) return '运行中'
  if (!status.value) return '空闲'
  const map: Record<string, string> = {
    completed: '已完成',
    planned: '已计划',
    failed: '失败',
    cancelled: '已取消',
    running: '运行中',
  }
  return map[status.value] ?? status.value
})

const statusDotClass = computed(() => {
  if (isRunning.value || status.value === 'running') return 'running'
  if (status.value === 'completed' || status.value === 'planned') return 'ok'
  if (status.value === 'failed') return 'fail'
  return 'idle'
})
</script>

<template>
  <section class="execution-workbench">
    <div class="bench-grid">
      <div class="bench-pane trace-pane">
        <header class="pane-header">执行轨迹</header>
        <div class="pane-body">
          <div v-if="physicalPlanTree" class="plan-tree">
            <LogicalPlanTreeNode :node="physicalPlanTree" />
          </div>
          <p v-else class="empty">运行查询后显示算子树</p>
        </div>
      </div>

      <div class="bench-pane stats-pane">
        <header class="pane-header">执行统计</header>
        <div class="pane-body">
          <template v-if="summary">
            <div class="stat-row">
              <span class="stat-label">扫描块</span>
              <span class="stat-value mono">{{ summary.scanned }} / {{ summary.scanned + summary.pruned }} ({{ summary.scannedPct }}%)</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">跳过块</span>
              <span class="stat-value mono">{{ summary.pruned }} ({{ summary.prunedPct }}%)</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">解码块</span>
              <span class="stat-value mono">{{ summary.decoded }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">读取量</span>
              <span class="stat-value mono">{{ formatBytes(summary.bytesRead) }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">输出行</span>
              <span class="stat-value mono">{{ summary.rowsOut }}</span>
            </div>
            <div v-if="summary.totalTime != null" class="stat-row">
              <span class="stat-label">耗时</span>
              <span class="stat-value mono">{{ formatDurationMs(summary.totalTime) }}</span>
            </div>
          </template>
          <p v-else class="empty">暂无执行统计</p>
        </div>
      </div>

      <div class="bench-pane filter-pane">
        <header class="pane-header">筛选条件</header>
        <div class="pane-body">
          <p v-if="filterText" class="filter-text mono">{{ filterText }}</p>
          <p v-else class="empty">暂无筛选条件</p>
        </div>
      </div>

      <div class="bench-pane status-pane">
        <header class="pane-header">运行状态</header>
        <div class="pane-body">
          <div class="status-line">
            <span class="status-dot" :class="statusDotClass" />
            <span class="status-label">{{ statusLabel }}</span>
          </div>
          <div v-if="runMeta.createdAt" class="meta-row">
            <span class="meta-label">开始</span>
            <span class="meta-value mono">{{ runMeta.createdAt }}</span>
          </div>
          <div v-if="currentQueryId" class="meta-row">
            <span class="meta-label">Query</span>
            <span class="meta-value mono">#{{ currentQueryId }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.execution-workbench {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-panel);
}

.bench-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns:
    minmax(260px, 1.45fr)
    minmax(150px, 0.8fr)
    minmax(170px, 0.95fr)
    minmax(150px, 0.8fr);
}

.bench-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  border-right: 1px solid var(--border-default);
}

.status-pane {
  border-right: none;
}

.pane-header {
  flex-shrink: 0;
  height: 27px;
  padding: 0 9px;
  display: flex;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-raised);
}

.pane-body {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: auto;
  overflow-x: hidden;
  padding: 7px 9px;
}

.plan-tree {
  font-size: 11px;
  line-height: 1.45;
}

.stat-row,
.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  min-height: 20px;
  font-size: 11px;
}

.stat-label,
.meta-label {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.stat-value,
.meta-value {
  color: var(--text-primary);
  text-align: right;
}

.filter-text {
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: var(--text-secondary);
  word-break: break-word;
}

.status-line {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 22px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary);
  flex-shrink: 0;
}

.status-dot.ok {
  background: var(--success);
}

.status-dot.running {
  background: var(--text-secondary);
}

.status-dot.fail {
  background: var(--danger);
}

.empty {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1.5;
}

@media (max-width: 900px) {
  .bench-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
  }

  .filter-pane {
    border-right: none;
  }

  .stats-pane,
  .trace-pane {
    border-bottom: 1px solid var(--border-default);
  }
}
</style>
