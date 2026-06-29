<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useWorkspaceLayoutStore } from '@/stores/workspaceLayoutStore'
import CodecCandidateTable from './CodecCandidateTable.vue'
import RleRunPreview from './RleRunPreview.vue'
import DictionaryPreview from './DictionaryPreview.vue'
import { getBlockPreview, type BlockPreview } from '@/api/datasets'
import { formatBlockLabel, formatBytes } from '@/utils/format'
import type { SelectedBlockMeta } from '@/stores/storageMapStore'

const props = defineProps<{
  selectedBlock?: SelectedBlockMeta | null
}>()

const layoutStore = useWorkspaceLayoutStore()

const loading = ref(false)
const preview = ref<BlockPreview | null>(null)
const loadError = ref<string | null>(null)

const blockTitle = computed(() => {
  if (!props.selectedBlock) return '块检查器'
  return `Block ${formatBlockLabel(props.selectedBlock.block_id)} / ${props.selectedBlock.column}`
})

const block = computed(() => {
  if (props.selectedBlock) {
    return {
      encoding: props.selectedBlock.encoding,
      row_start: props.selectedBlock.row_start,
      row_count: props.selectedBlock.row_count,
      crc32: props.selectedBlock.payload_crc32,
    }
  }
  return preview.value?.block ?? null
})

const compressionRatio = computed(() => {
  const stats = preview.value?.stats
  const raw = stats?.raw_bytes ?? props.selectedBlock?.raw_bytes
  const encoded = stats?.encoded_bytes ?? props.selectedBlock?.encoded_bytes
  if (!raw) return '—'
  return `${((1 - (encoded ?? 0) / raw) * 100).toFixed(1)}%`
})

const rawSize = computed(() => {
  const bytes = preview.value?.stats?.raw_bytes ?? props.selectedBlock?.raw_bytes
  return bytes != null ? formatBytes(bytes) : '—'
})

const compressedSize = computed(() => {
  const bytes = preview.value?.stats?.encoded_bytes ?? props.selectedBlock?.encoded_bytes
  return bytes != null ? formatBytes(bytes) : '—'
})

async function loadPreview() {
  preview.value = null
  loadError.value = null
  const sel = props.selectedBlock
  if (!sel) return
  loading.value = true
  try {
    preview.value = await getBlockPreview(sel.column_id, sel.block_id)
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : '加载块预览失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.selectedBlock, loadPreview, { immediate: true, deep: true })
</script>

<template>
  <aside class="block-inspector">
    <div class="panel-header">
      <span class="panel-title">{{ blockTitle }}</span>
      <button type="button" class="collapse-btn" title="折叠面板" @click="layoutStore.toggleRight()">
        ›
      </button>
    </div>
    <div class="panel-body">
      <p v-if="!selectedBlock" class="hint">点击列块轨道中的块查看元数据、编码候选与结构摘要。</p>
      <p v-else-if="loading" class="hint">加载块预览…</p>
      <p v-else-if="loadError" class="hint error">{{ loadError }}</p>
      <template v-else-if="selectedBlock && block">
        <dl class="meta-list">
          <div><dt>编码</dt><dd>{{ block.encoding }}</dd></div>
          <div><dt>起始行</dt><dd class="mono">{{ block.row_start.toLocaleString() }}</dd></div>
          <div><dt>行数</dt><dd class="mono">{{ block.row_count.toLocaleString() }}</dd></div>
          <div><dt>原始大小</dt><dd class="mono">{{ rawSize }}</dd></div>
          <div><dt>压缩大小</dt><dd class="mono">{{ compressedSize }}</dd></div>
          <div><dt>压缩比</dt><dd class="mono">{{ compressionRatio }}</dd></div>
          <div v-if="preview?.stats?.min_repr"><dt>min</dt><dd class="mono">{{ preview.stats.min_repr }}</dd></div>
          <div v-if="preview?.stats?.max_repr"><dt>max</dt><dd class="mono">{{ preview.stats.max_repr }}</dd></div>
          <div v-if="preview?.stats"><dt>NULL</dt><dd class="mono">{{ preview.stats.null_count }}</dd></div>
          <div v-if="preview?.stats"><dt>distinct</dt><dd class="mono">{{ preview.stats.distinct_count }}</dd></div>
          <div><dt>CRC32</dt><dd class="mono">{{ block.crc32 }}</dd></div>
          <div v-if="selectedBlock.prune_state"><dt>裁剪状态</dt><dd class="mono">{{ selectedBlock.prune_state }}</dd></div>
          <div v-if="selectedBlock.prune_reason"><dt>跳过理由</dt><dd class="mono prune-reason">{{ selectedBlock.prune_reason }}</dd></div>
        </dl>
        <template v-if="preview">
          <div class="section-title">编码候选 (估算压缩后大小)</div>
          <CodecCandidateTable :candidates="preview.candidates" />
          <div class="final-selection">
            <div><span class="final-label">最终选择:</span> <span class="mono">{{ preview.winner_encoding }}</span></div>
            <div><span class="final-label">选择依据:</span> <span class="mono reason">{{ preview.selection_reason }}</span></div>
          </div>
          <div v-if="preview.rle_runs?.length" class="section-block">
            <div class="section-title">RLE 游程摘要</div>
            <RleRunPreview :runs="preview.rle_runs" />
          </div>
          <div v-if="preview.dictionary" class="section-block">
            <div class="section-title">Dictionary 摘要</div>
            <DictionaryPreview :dictionary="preview.dictionary" />
          </div>
        </template>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.block-inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-panel);
  border-left: 1px solid var(--border-default);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-raised);
  flex-shrink: 0;
}

.panel-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collapse-btn {
  width: 20px;
  height: 20px;
  padding: 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  font-size: 14px;
  line-height: 1;
  color: var(--text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
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

.hint.error {
  color: #b91c1c;
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

.final-selection {
  margin-top: 10px;
  padding: 8px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-muted);
  font-size: 11px;
  line-height: 1.6;
}

.final-label {
  color: var(--text-tertiary);
}

.reason {
  color: var(--text-secondary);
  word-break: break-word;
}

.prune-reason {
  color: #b91c1c;
  word-break: break-word;
}
</style>
