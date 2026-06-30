<script setup lang="ts">
defineProps<{
  rows: Array<{ encoding: string; size: string; selected: boolean }>
}>()
</script>

<template>
  <section class="codec-competition">
    <div class="section-title">编码候选</div>
    <table class="competition-table">
      <thead>
        <tr>
          <th>编码</th>
          <th>估算大小</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.encoding" :class="{ selected: row.selected }">
          <td class="enc-name">{{ row.encoding }}</td>
          <td class="enc-size mono">{{ row.size }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.codec-competition {
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

.competition-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}

.competition-table th {
  padding: 4px 8px;
  text-align: left;
  font-weight: 500;
  font-size: 12px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
}

.competition-table th:last-child {
  text-align: right;
  width: 96px;
}

.competition-table td {
  padding: 5px 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.competition-table tr.selected {
  background: var(--state-active-bg);
  box-shadow: inset 2px 0 0 var(--state-active-border);
}

.competition-table tr.selected .enc-name {
  font-weight: 600;
}

.enc-name {
  color: var(--text-primary);
}

.enc-size {
  text-align: right;
  color: var(--text-primary);
}
</style>
