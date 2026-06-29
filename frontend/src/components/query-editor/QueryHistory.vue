<script setup lang="ts">
import type { QueryHistoryItem } from '@/api/queries'

defineProps<{
  items: QueryHistoryItem[]
}>()

const emit = defineEmits<{
  select: [item: QueryHistoryItem]
}>()
</script>

<template>
  <aside class="query-history">
    <div class="history-title">查询历史</div>
    <ul v-if="items.length" class="history-list">
      <li v-for="item in items" :key="item.id">
        <button type="button" class="history-item" @click="emit('select', item)">
          <span class="status" :class="item.status">{{ item.status }}</span>
          <span class="sql mono">{{ item.sql_text }}</span>
        </button>
      </li>
    </ul>
    <p v-else class="empty">暂无历史记录</p>
  </aside>
</template>

<style scoped>
.query-history {
  border-right: 1px solid var(--border-default);
  min-width: 160px;
  max-width: 220px;
  overflow: auto;
  background: var(--bg-muted);
  font-size: 11px;
}

.history-title {
  padding: 6px 8px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
}

.history-list {
  list-style: none;
  margin: 0;
  padding: 4px;
}

.history-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  text-align: left;
  padding: 6px;
  border: none;
  border-radius: var(--radius-control);
  background: transparent;
  cursor: pointer;
}

.history-item:hover {
  background: var(--bg-panel);
}

.status {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.status.planned {
  color: #15803d;
}

.status.failed {
  color: #b91c1c;
}

.sql {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--text-primary);
  line-height: 1.4;
}

.empty {
  margin: 8px;
  color: var(--text-tertiary);
}
</style>
