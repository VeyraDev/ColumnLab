<script setup lang="ts">
defineProps<{
  rows: Array<{ label: string; value: string }>
}>()
</script>

<template>
  <section class="final-decision">
    <div class="section-title">最终选择</div>
    <dl class="decision-grid">
      <div v-for="row in rows" :key="row.label" class="decision-row">
        <dt>{{ row.label }}</dt>
        <dd class="mono">{{ row.value }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.final-decision {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.decision-grid {
  margin: 0;
}

.decision-row {
  display: grid;
  grid-template-columns: 112px 1fr;
  gap: 8px;
  min-height: 24px;
  align-items: baseline;
  font-size: 13px;
}

.decision-row dt {
  color: var(--text-secondary);
  font-size: 12px;
}

.decision-row dd {
  margin: 0;
  color: var(--text-primary);
  text-align: right;
  word-break: break-word;
}
</style>
