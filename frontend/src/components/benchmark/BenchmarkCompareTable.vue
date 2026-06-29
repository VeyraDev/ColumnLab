<script setup lang="ts">
defineProps<{
  rows: Array<{ column: string; encoding: string; mean: number; p95: number }>
}>()

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toFixed(0)
}
</script>

<template>
  <section class="compare-table">
    <h2>编码字节对比（mean / p95）</h2>
    <table>
      <thead>
        <tr>
          <th>列</th>
          <th>编码</th>
          <th>mean 字节</th>
          <th>p95 字节</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="`${row.column}-${row.encoding}`">
          <td>{{ row.column }}</td>
          <td>{{ row.encoding }}</td>
          <td>{{ fmt(row.mean) }}</td>
          <td>{{ fmt(row.p95) }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.compare-table {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 10px 12px;
  background: var(--bg-panel);
}

h2 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

th,
td {
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-subtle, var(--border-default));
}

th {
  color: var(--text-tertiary);
  font-weight: 500;
}
</style>
