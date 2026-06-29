<script setup lang="ts">
import { computed } from 'vue'
import type { QueryError } from '@/api/queries'

const sql = defineModel<string>({ required: true })
const props = defineProps<{
  error?: QueryError | null
  loading?: boolean
  running?: boolean
}>()

const emit = defineEmits<{
  run: []
  cancel: []
}>()

const errorText = computed(() => {
  if (!props.error?.message) return null
  if (props.error.line != null) {
    const col = props.error.col ?? 1
    return `${props.error.line}:${col} ${props.error.message}`
  }
  return props.error.message
})

function onKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    emit('run')
  }
}
</script>

<template>
  <div class="query-editor">
    <div class="editor-toolbar">
      <span class="toolbar-title">SQL 查询</span>
      <div class="toolbar-actions">
        <button
          v-if="running"
          type="button"
          class="btn-cancel"
          @click="emit('cancel')"
        >
          取消
        </button>
        <button type="button" class="btn-run" :disabled="loading && !running" @click="emit('run')">
          {{ loading ? '执行中…' : '运行 (Ctrl+Enter)' }}
        </button>
      </div>
    </div>
    <div v-if="errorText" class="error-bar mono">{{ errorText }}</div>
    <textarea
      v-model="sql"
      class="sql-input mono"
      spellcheck="false"
      rows="4"
      placeholder="SELECT col FROM table_name WHERE …"
      @keydown="onKeydown"
    />
  </div>
</template>

<style scoped>
.query-editor {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-panel);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--border-default);
}

.toolbar-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.toolbar-actions {
  display: flex;
  gap: 6px;
}

.btn-run {
  height: 26px;
  padding: 0 10px;
  border-radius: var(--radius-control);
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
  font-size: 11px;
  cursor: pointer;
}

.btn-cancel {
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--border-default);
  background: var(--bg-panel);
  font-size: 11px;
  cursor: pointer;
}

.btn-run:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-bar {
  padding: 4px 10px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 11px;
  border-bottom: 1px solid #fecaca;
}

.sql-input {
  flex: 0 0 auto;
  height: 108px;
  min-height: 72px;
  max-height: 240px;
  border: none;
  resize: vertical;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
  background: var(--bg-panel);
  color: var(--text-primary);
  outline: none;
}
</style>
