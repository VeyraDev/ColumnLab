<script setup lang="ts">
defineProps<{
  rows: Array<{ label: string; value: string }>
}>()
</script>

<template>
  <dl class="metadata-grid">
    <div v-for="row in rows" :key="row.label" class="meta-row">
      <dt>{{ row.label }}</dt>
      <dd class="mono">{{ row.value }}</dd>
    </div>
  </dl>
</template>

<style scoped>
.metadata-grid {
  margin: 0;
}

.meta-row {
  display: grid;
  grid-template-columns: 112px 1fr;
  gap: 8px;
  min-height: 24px;
  align-items: baseline;
  font-size: 13px;
}

.meta-row dt {
  color: var(--text-secondary);
  font-size: 12px;
}

.meta-row dd {
  margin: 0;
  color: var(--text-primary);
  text-align: right;
  word-break: break-word;
}
</style>
