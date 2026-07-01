<script setup lang="ts">
import { codecReasonLabel, encodingLabel } from '@/utils/terminology'

export interface CodecCandidateRow {
  encoding: string
  encoded_bytes: number
  raw_bytes?: number
  gain?: number
  encode_ns?: number
  selected: boolean
  reason?: string
  size?: string
}

const props = defineProps<{
  rows: CodecCandidateRow[]
}>()

function formatKiB(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KiB`
}

function formatGain(gain: number | undefined, encoded: number, raw: number | undefined): string {
  if (gain != null) return `${(gain * 100).toFixed(1)}%`
  if (raw && raw > 0) return `${((1 - encoded / raw) * 100).toFixed(1)}%`
  return '—'
}

function formatEncodeNs(ns: number | undefined): string {
  if (ns == null) return '—'
  if (ns < 1_000_000) return `${(ns / 1000).toFixed(1)} µs`
  return `${(ns / 1_000_000).toFixed(2)} ms`
}
</script>

<template>
  <section class="codec-competition">
    <div class="section-title">编码候选</div>
    <table class="competition-table">
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
        <tr v-for="row in rows" :key="row.encoding" :class="{ selected: row.selected }">
          <td class="enc-name" :title="row.encoding">{{ encodingLabel(row.encoding) }}</td>
          <td class="enc-size mono">{{ row.size ?? formatKiB(row.encoded_bytes) }}</td>
          <td class="mono">{{ formatGain(row.gain, row.encoded_bytes, row.raw_bytes) }}</td>
          <td class="mono">{{ formatEncodeNs(row.encode_ns) }}</td>
          <td>
            <span v-if="row.selected" class="tag selected-tag">已选</span>
            <span v-if="row.reason" class="reason" :title="row.reason">{{ codecReasonLabel(row.reason) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p class="table-note">
      候选结果是在查看块时重新编码计算得到。单次编码耗时只用于观察算法开销，不代表导入总耗时或正式 Benchmark 结果。
    </p>
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
  font-size: 12px;
  table-layout: fixed;
}

.competition-table th {
  padding: 4px 6px;
  text-align: left;
  font-weight: 500;
  font-size: 11px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
}

.competition-table td {
  padding: 5px 6px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: top;
}

.competition-table tr.selected {
  background: var(--state-active-bg);
  box-shadow: inset 2px 0 0 var(--state-active-border);
}

.enc-name {
  color: var(--text-primary);
  font-weight: 500;
}

.enc-size {
  color: var(--text-primary);
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
  color: var(--text-secondary);
  font-size: 11px;
}

.table-note {
  margin: 8px 0 0;
  font-size: 11px;
  line-height: 1.45;
  color: var(--text-tertiary);
}
</style>
