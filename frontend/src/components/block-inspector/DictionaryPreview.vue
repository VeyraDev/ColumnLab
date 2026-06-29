<script setup lang="ts">
export interface DictionaryPreviewData {
  dictionary_count: number
  bit_width: number
  entries: Array<string | number | boolean>
  packed_codes_hex: string
  sample_codes: number[]
  row_count?: number
}

defineProps<{
  dictionary: DictionaryPreviewData
}>()
</script>

<template>
  <div class="dict-preview">
    <div class="meta mono">
      字典 {{ dictionary.dictionary_count }} 项 · code 位宽 {{ dictionary.bit_width }}
    </div>
    <table class="dict-table">
      <thead>
        <tr><th>code</th><th>值</th></tr>
      </thead>
      <tbody>
        <tr v-for="(entry, code) in dictionary.entries" :key="code">
          <td class="mono">{{ code }}</td>
          <td class="mono">{{ entry }}</td>
        </tr>
      </tbody>
    </table>
    <div class="packed">
      <div class="label">packed codes（前 16 字节）</div>
      <code class="mono">{{ dictionary.packed_codes_hex }}</code>
    </div>
    <div class="packed">
      <div class="label">样本 codes</div>
      <code class="mono">{{ dictionary.sample_codes.join(', ') }}</code>
    </div>
  </div>
</template>

<style scoped>
.dict-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11px;
}

.meta {
  color: var(--text-secondary);
}

.dict-table {
  width: 100%;
  border-collapse: collapse;
}

.dict-table th,
.dict-table td {
  border: 1px solid var(--border-default);
  padding: 4px 6px;
  text-align: left;
}

.dict-table th {
  background: var(--bg-muted);
  color: var(--text-secondary);
}

.packed .label {
  color: var(--text-tertiary);
  margin-bottom: 2px;
}

.packed code {
  display: block;
  word-break: break-all;
  color: var(--text-secondary);
}
</style>
