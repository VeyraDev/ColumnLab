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
  <div class="rle-preview">
    <p class="explain">
      RLE 保存「值 + 连续重复次数」，例如 A A A B B 保存为 (A,3)、(B,2)。
    </p>
    <table class="run-table">
      <thead>
        <tr>
          <th>起始行偏移</th>
          <th>值</th>
          <th>连续重复次数</th>
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
  </div>
</template>

<style scoped>
.explain {
  margin: 0 0 8px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--text-secondary);
}

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
