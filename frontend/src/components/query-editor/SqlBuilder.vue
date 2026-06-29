<script setup lang="ts">
const props = defineProps<{
  tableName: string
  columns: Array<{ name: string; logical_type: string }>
}>()

const emit = defineEmits<{
  insert: [snippet: string]
}>()

function insertSelect(col: string) {
  emit('insert', `SELECT ${col} FROM ${props.tableName} LIMIT 10`)
}

function insertWhere(col: string, type: string) {
  const lit = type === 'INT64' || type.includes('FLOAT') ? '0' : "'value'"
  emit('insert', `SELECT ${col} FROM ${props.tableName} WHERE ${col} > ${lit}`)
}
</script>

<template>
  <div v-if="columns.length" class="sql-builder">
    <span class="builder-label">构造器</span>
    <div class="builder-cols">
      <button
        v-for="col in columns"
        :key="col.name"
        type="button"
        class="col-chip mono"
        :title="col.logical_type"
        @click="insertSelect(col.name)"
      >
        {{ col.name }}
      </button>
    </div>
    <div class="builder-cols">
      <button
        v-for="col in columns"
        :key="`${col.name}-where`"
        type="button"
        class="where-chip mono"
        @click="insertWhere(col.name, col.logical_type)"
      >
        WHERE {{ col.name }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.sql-builder {
  padding: 6px 10px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-muted);
}

.builder-label {
  font-size: 10px;
  color: var(--text-tertiary);
  margin-right: 8px;
}

.builder-cols {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.col-chip,
.where-chip {
  height: 22px;
  padding: 0 8px;
  border: 1px solid var(--border-default);
  background: var(--bg-panel);
  font-size: 10px;
  cursor: pointer;
}

.col-chip:hover,
.where-chip:hover {
  border-color: var(--accent);
}
</style>
