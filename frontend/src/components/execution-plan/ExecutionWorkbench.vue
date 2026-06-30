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
  return {
    scanned: m.scanned_blocks,
    pruned: m.pruned_blocks,
    total,
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
  return sql.length > 120 ? `${sql.slice(0, 120)}…` : sql
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
      <div class="bench-card trace-pane">
        <header class="card-header">执行轨迹</header>
        <div class="card-body">
          <div v-if="physicalPlanTree" class="plan-tree mono">
            <LogicalPlanTreeNode :node="physicalPlanTree" />
          </div>
          <p v-else class="empty">运行查询后显示算子树</p>
        </div>
      </div>

      <div class="bench-card stats-pane">
        <header class="card-header">执行统计</header>
        <div class="card-body">
          <template v-if="summary">
            <div class="stat-row">
              <span class="stat-label">扫描块</span>
              <span class="stat-value mono">{{ summary.scanned }} / {{ summary.total }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">跳过块</span>
              <span class="stat-value mono">{{ summary.pruned }}</span>
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

      <div class="bench-card filter-pane">
        <header class="card-header">筛选条件</header>
        <div class="card-body">
          <p v-if="filterText" class="filter-text mono">{{ filterText }}</p>
          <p v-else class="empty">暂无筛选条件</p>
        </div>
      </div>

      <div class="bench-card status-pane">
        <header class="card-header">运行状态</header>
        <div class="card-body">
          <div class="status-line">
            <span class="status-dot" :class="statusDotClass" />
            <span class="status-label">{{ statusLabel }}</span>
          </div>
          <div v-if="runMeta.createdAt" class="meta-row">
            <span class="meta-label">开始时间</span>
            <span class="meta-value mono">{{ runMeta.createdAt }}</span>
          </div>
          <div v-if="summary?.totalTime != null" class="meta-row">
            <span class="meta-label">查询耗时</span>
            <span class="meta-value mono">{{ formatDurationMs(summary.totalTime) }}</span>
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
  height: 100%;
  min-height: 0;
  padding: 4px;
  background: var(--bg-app);
}

.bench-grid {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: 1.45fr 0.8fr 0.9fr 0.8fr;
  gap: var(--workspace-panel-gap);
}

.bench-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: var(--bg-panel);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  overflow: hidden;
}

.card-header {
  flex-shrink: 0;
  height: 32px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-raised);
}

.card-body {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: auto;
  overflow-x: hidden;
  padding: 6px 8px;
}

.plan-tree {
  font-size: 13px;
  line-height: 20px;
  color: var(--text-primary);
}

.stat-row,
.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
  min-height: 22px;
  font-size: 13px;
}

.stat-label,
.meta-label {
  color: var(--text-secondary);
  flex-shrink: 0;
}

.stat-value,
.meta-value {
  color: var(--text-primary);
  text-align: right;
}

.filter-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-primary);
  word-break: break-word;
}

.status-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
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
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
}

@media (max-width: 1200px) {
  .bench-grid {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
  }
}
</style>
