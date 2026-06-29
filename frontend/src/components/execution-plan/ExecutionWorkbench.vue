<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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
} = storeToRefs(queryStore)

const summary = computed(() => {
  const m = metrics.value
  if (!m) return null
  return {
    scanned: m.scanned_blocks,
    pruned: m.pruned_blocks,
    decoded: m.decoded_blocks,
    bytesRead: m.bytes_read,
    rowsOut: m.rows_output,
    cacheHits: m.cache_hits,
    elapsed: m.execute_time,
  }
})

const filterText = computed(() => {
  const sql = sqlText.value.trim()
  if (!sql) return null
  const match = sql.match(/\bwhere\b([\s\S]*?)(?:\bgroup\b|\border\b|\blimit\b|$)/i)
  if (match?.[1]?.trim()) return `WHERE ${match[1].trim()}`
  const group = sql.match(/\bgroup\s+by\b[\s\S]*/i)
  if (group) return group[0].trim()
  return sql.length > 120 ? `${sql.slice(0, 120)}…` : sql
})

const runMeta = computed(() => {
  const item = history.value[0]
  return {
    createdAt: item?.created_at ?? null,
    threadCount: 1,
  }
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
    <div class="bench-pane trace-pane">
      <header class="pane-header">执行轨迹</header>
      <div class="pane-body">
        <div v-if="physicalPlanTree" class="plan-tree">
          <LogicalPlanTreeNode :node="physicalPlanTree" />
        </div>
        <p v-else class="empty">运行查询后显示物理算子树</p>
      </div>
    </div>

    <div class="bench-pane stats-pane">
      <header class="pane-header">执行统计</header>
      <div class="pane-body">
        <dl v-if="summary" class="stats-list">
          <div><dt>扫描块数</dt><dd class="mono">{{ summary.scanned }}</dd></div>
          <div><dt>跳过块数</dt><dd class="mono">{{ summary.pruned }}</dd></div>
          <div><dt>解码块数</dt><dd class="mono">{{ summary.decoded }}</dd></div>
          <div><dt>读取数据量</dt><dd class="mono">{{ formatBytes(summary.bytesRead) }}</dd></div>
          <div><dt>输出行数</dt><dd class="mono">{{ summary.rowsOut }}</dd></div>
          <div><dt>缓存命中</dt><dd class="mono">{{ summary.cacheHits }}</dd></div>
          <div><dt>耗时</dt><dd class="mono">{{ formatDurationMs(summary.elapsed) }}</dd></div>
        </dl>
        <p v-else class="empty">暂无执行统计</p>
      </div>
    </div>

    <div class="bench-pane filter-pane">
      <header class="pane-header">筛选条件</header>
      <div class="pane-body">
        <pre v-if="filterText" class="filter-box mono">{{ filterText }}</pre>
        <p v-else class="empty">运行查询后显示 WHERE / GROUP BY 条件</p>
      </div>
    </div>

    <div class="bench-pane status-pane">
      <header class="pane-header">运行状态</header>
      <div class="pane-body">
        <div class="status-row">
          <span class="status-dot" :class="statusDotClass" />
          <span class="status-text">{{ statusLabel }}</span>
        </div>
        <dl class="meta-list">
          <div v-if="runMeta.createdAt">
            <dt>开始</dt>
            <dd class="mono">{{ runMeta.createdAt }}</dd>
          </div>
          <div v-if="summary?.elapsed != null">
            <dt>总耗时</dt>
            <dd class="mono">{{ formatDurationMs(summary.elapsed) }}</dd>
          </div>
          <div>
            <dt>线程数</dt>
            <dd class="mono">{{ runMeta.threadCount }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </section>
</template>

<style scoped>
.execution-workbench {
  display: grid;
  grid-template-columns: 1.2fr 0.9fr 1fr 0.8fr;
  height: 100%;
  min-height: 0;
  background: var(--bg-panel);
}

.bench-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  border-right: 1px solid var(--border-default);
}

.bench-pane:last-child {
  border-right: none;
}

.pane-header {
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-raised);
  flex-shrink: 0;
}

.pane-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px 10px;
}

.plan-tree {
  font-size: 11px;
}

.stats-list,
.meta-list {
  margin: 0;
}

.stats-list div,
.meta-list div {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px;
  padding: 3px 0;
  font-size: 11px;
}

.stats-list dt,
.meta-list dt {
  color: var(--text-tertiary);
}

.stats-list dd,
.meta-list dd {
  margin: 0;
  color: var(--text-primary);
}

.filter-box {
  margin: 0;
  padding: 8px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-muted);
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.status-dot.ok {
  background: var(--success);
}

.status-dot.running {
  background: var(--accent);
}

.status-dot.fail {
  background: var(--danger);
}

.status-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.empty {
  margin: 0;
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1.5;
}

@media (max-width: 1366px) {
  .execution-workbench {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
  }
}
</style>
