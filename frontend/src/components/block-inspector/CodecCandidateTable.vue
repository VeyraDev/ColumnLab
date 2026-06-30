<script setup lang="ts">
export interface CodecCandidate {
  encoding: string
  encoded_bytes: number
  raw_bytes: number
  gain: number
  encode_ns: number
  selected: boolean
  reason: string
}

defineProps<{
  candidates: CodecCandidate[]
}>()

function formatKiB(bytes: number): string {
  return `${(bytes / 1024).toFixed(1)} KiB`
}

function formatGain(gain: number): string {
  return `${(gain * 100).toFixed(1)}%`
}
</script>

<template>
  <table class="candidate-table">
    <thead>
      <tr>
        <th>算法</th>
        <th>大小</th>
        <th>收益</th>
        <th>耗时</th>
        <th>结果</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in candidates" :key="row.encoding" :class="{ selected: row.selected }">
        <td>{{ row.encoding }}</td>
        <td class="mono">{{ formatKiB(row.encoded_bytes) }}</td>
        <td class="mono">{{ formatGain(row.gain) }}</td>
        <td class="mono">{{ (row.encode_ns / 1_000_000).toFixed(2) }} ms</td>
        <td>
          <span v-if="row.selected" class="tag selected-tag">已选</span>
          <span class="reason">{{ row.reason }}</span>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.candidate-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.candidate-table th,
.candidate-table td {
  border: 1px solid var(--border-default);
  padding: 4px 6px;
  text-align: left;
  vertical-align: top;
}

.candidate-table th {
  background: var(--bg-muted);
  color: var(--text-secondary);
  font-weight: 500;
}

.candidate-table tr.selected {
  background: var(--state-active-bg);
  box-shadow: inset 2px 0 0 var(--state-active-border);
}

.tag {
  display: inline-block;
  margin-right: 4px;
  padding: 0 4px;
  border-radius: 2px;
  font-size: 10px;
}

.selected-tag {
  background: var(--accent);
  color: #fff;
}

.reason {
  color: var(--text-tertiary);
}
</style>
