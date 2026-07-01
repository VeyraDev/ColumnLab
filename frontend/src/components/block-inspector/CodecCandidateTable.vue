<script setup lang="ts">
import { codecReasonLabel, encodingLabel } from '@/utils/terminology'

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
  if (bytes < 1024) return `${bytes} B`
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
        <th>编码</th>
        <th>编码载荷</th>
        <th>相比 RAW 节省</th>
        <th>单次编码耗时</th>
        <th>选择结果</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in candidates" :key="row.encoding" :class="{ selected: row.selected }">
        <td :title="row.encoding">{{ encodingLabel(row.encoding) }}</td>
        <td class="mono">{{ formatKiB(row.encoded_bytes) }}</td>
        <td class="mono">{{ formatGain(row.gain) }}</td>
        <td class="mono">{{ (row.encode_ns / 1_000_000).toFixed(2) }} ms</td>
        <td>
          <span v-if="row.selected" class="tag selected-tag">已选</span>
          <span class="reason" :title="row.reason">{{ codecReasonLabel(row.reason) }}</span>
        </td>
      </tr>
    </tbody>
  </table>
  <p class="table-note">
    候选结果是在查看块时重新编码计算得到。单次编码耗时只用于观察算法开销，不代表导入总耗时或正式 Benchmark 结果。
  </p>
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

.table-note {
  margin: 8px 0 0;
  font-size: 11px;
  line-height: 1.45;
  color: var(--text-tertiary);
}
</style>
