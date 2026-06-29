<script setup lang="ts">
export interface RleRun {
  value: string | number | boolean
  run_length: number
  start: number
}

defineProps<{
  runs: RleRun[]
}>()
</script>

<template>
  <table class="run-table">
    <thead>
      <tr>
        <th>起始行</th>
        <th>值</th>
        <th>游程长度</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(run, idx) in runs" :key="idx">
        <td class="mono">{{ run.start }}</td>
        <td class="mono">{{ run.value }}</td>
        <td class="mono">{{ run.run_length }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.run-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.run-table th,
.run-table td {
  border: 1px solid var(--border-default);
  padding: 4px 6px;
  text-align: left;
}

.run-table th {
  background: var(--bg-muted);
  color: var(--text-secondary);
}
</style>
