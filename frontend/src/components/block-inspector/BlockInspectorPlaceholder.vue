<script setup lang="ts">
import { computed } from 'vue'
import EncodingLegend from './EncodingLegend.vue'
import CodecCandidateTable from './CodecCandidateTable.vue'
import RleRunPreview from './RleRunPreview.vue'
import DictionaryPreview from './DictionaryPreview.vue'
import codecFixture from '@/fixtures/codec-selection.json'

export type SelectedBlockMeta = {
  column: string
  block_id: number
  encoding: string
  row_start: number
  row_count: number
  compressed_bytes: number
  encoded_bytes: number
  raw_bytes: number
  payload_crc32: string
  prune_state?: string
  prune_reason?: string
}

const props = defineProps<{
  selectedBlock?: SelectedBlockMeta | null
}>()

const data = codecFixture as {
  selection_reason: string
  winner_encoding: string
  candidates: Array<{
    encoding: string
    encoded_bytes: number
    raw_bytes: number
    gain: number
    encode_ns: number
    selected: boolean
    reason: string
  }>
  rle_runs?: Array<{ value: string; run_length: number; start: number }>
  dictionary?: {
    dictionary_count: number
    bit_width: number
    entries: string[]
    packed_codes_hex: string
    sample_codes: number[]
  }
  block?: {
    encoding: string
    row_start: number
    row_count: number
    crc32: string
  }
}

const block = computed(() => {
  if (props.selectedBlock) {
    return {
      encoding: props.selectedBlock.encoding,
      row_start: props.selectedBlock.row_start,
      row_count: props.selectedBlock.row_count,
      crc32: props.selectedBlock.payload_crc32,
    }
  }
  return (
    data.block ?? {
      encoding: data.winner_encoding,
      row_start: 6144,
      row_count: 1024,
      crc32: 'a3f21c8b',
    }
  )
})

const compressionRatio = computed(() => {
  if (props.selectedBlock) {
    const { raw_bytes, encoded_bytes } = props.selectedBlock
    if (!raw_bytes) return '—'
    return `${((1 - encoded_bytes / raw_bytes) * 100).toFixed(1)}%`
  }
  const winner = data.candidates.find((c) => c.selected)
  if (!winner) return '—'
  return `${((1 - winner.encoded_bytes / winner.raw_bytes) * 100).toFixed(1)}%`
})

const note = computed(() =>
  props.selectedBlock
    ? `Stage 3 存储映射 · ${props.selectedBlock.column}`
    : `Stage 2 测试夹具 · ${data.selection_reason}`,
)
</script>

<template>
  <aside class="block-inspector">
    <div class="panel-header">
      <span>块检查器</span>
      <EncodingLegend />
    </div>
    <div class="panel-body">
      <p class="hint fixture-note">{{ note }}</p>
      <dl class="meta-list">
        <div><dt>编码</dt><dd>{{ block.encoding }}</dd></div>
        <div><dt>起始行</dt><dd class="mono">{{ block.row_start }}</dd></div>
        <div><dt>行数</dt><dd class="mono">{{ block.row_count }}</dd></div>
        <div><dt>压缩比</dt><dd class="mono">{{ compressionRatio }}</dd></div>
        <div><dt>CRC32</dt><dd class="mono">{{ block.crc32 }}</dd></div>
        <div v-if="selectedBlock?.prune_state"><dt>裁剪状态</dt><dd class="mono">{{ selectedBlock.prune_state }}</dd></div>
        <div v-if="selectedBlock?.prune_reason"><dt>跳过理由</dt><dd class="mono prune-reason">{{ selectedBlock.prune_reason }}</dd></div>
        <div v-if="selectedBlock"><dt>块大小</dt><dd class="mono">{{ selectedBlock.compressed_bytes }} B</dd></div>
      </dl>
      <template v-if="!selectedBlock">
        <div class="section-title">编码候选</div>
        <CodecCandidateTable :candidates="data.candidates" />
        <div v-if="data.rle_runs?.length" class="section-block">
          <div class="section-title">RLE 游程摘要</div>
          <RleRunPreview :runs="data.rle_runs" />
        </div>
        <div v-if="data.dictionary" class="section-block">
          <div class="section-title">Dictionary 摘要</div>
          <DictionaryPreview :dictionary="data.dictionary" />
        </div>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.block-inspector {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-panel);
  border-left: 1px solid var(--border-default);
}

.panel-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 10px;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-raised);
}

.panel-body {
  flex: 1;
  overflow: auto;
  padding: 10px;
  min-height: 0;
}

.hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.5;
}

.fixture-note {
  font-size: 11px;
}

.meta-list {
  margin: 0 0 12px;
}

.meta-list div {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 8px;
  padding: 3px 0;
  font-size: 12px;
}

.meta-list dt {
  color: var(--text-tertiary);
}

.meta-list dd {
  margin: 0;
  color: var(--text-primary);
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.section-block {
  margin-top: 12px;
}

.prune-reason {
  color: #b91c1c;
  word-break: break-word;
}
</style>
