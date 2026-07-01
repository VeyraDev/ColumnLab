<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'
import { useWorkspaceLayoutStore } from '@/stores/workspaceLayoutStore'
import BlockMetadataGrid from './BlockMetadataGrid.vue'
import CodecCompetitionTable from './CodecCompetitionTable.vue'
import FinalCodecDecision from './FinalCodecDecision.vue'
import RleRunPreview from './RleRunPreview.vue'
import DictionaryPreview from './DictionaryPreview.vue'
import { getBlockPreview, type BlockPreview } from '@/api/datasets'
import { formatBlockLabel, formatBytes } from '@/utils/format'
import { codecReasonLabel } from '@/utils/terminology'
import type { SelectedBlockMeta } from '@/stores/storageMapStore'

const props = defineProps<{
  selectedBlock?: SelectedBlockMeta | null
}>()

const layoutStore = useWorkspaceLayoutStore()
const structureOpen = ref(false)
const loading = ref(false)
const preview = ref<BlockPreview | null>(null)
const loadError = ref<string | null>(null)

const blockLabel = computed(() => {
  if (!props.selectedBlock) return '—'
  return `Block ${formatBlockLabel(props.selectedBlock.block_id)} / ${props.selectedBlock.column}`
})

const winnerEncoding = computed(
  () => preview.value?.winner_encoding ?? props.selectedBlock?.encoding ?? '—',
)

const rawBytes = computed(
  () => preview.value?.stats?.raw_bytes ?? props.selectedBlock?.raw_bytes ?? 0,
)

const encodedBytes = computed(
  () => preview.value?.stats?.encoded_bytes ?? props.selectedBlock?.encoded_bytes ?? 0,
)

const compressionPct = computed(() => {
  if (!rawBytes.value) return '—'
  return `${((1 - encodedBytes.value / rawBytes.value) * 100).toFixed(1)}%`
})

const metadataRows = computed(() => {
  const sel = props.selectedBlock
  if (!sel) return []
  const stats = preview.value?.stats
  const rows = [
    { label: '编码方式', value: winnerEncoding.value },
    { label: '起始行', value: sel.row_start.toLocaleString() },
    { label: '行数', value: sel.row_count.toLocaleString() },
    { label: '原始大小', value: formatBytes(rawBytes.value) },
    { label: '压缩后大小', value: formatBytes(encodedBytes.value) },
    { label: '压缩率', value: compressionPct.value },
  ]
  if (stats?.min_repr != null) rows.push({ label: 'min', value: stats.min_repr })
  if (stats?.max_repr != null) rows.push({ label: 'max', value: stats.max_repr })
  if (stats) {
    rows.push({ label: 'distinct_count', value: String(stats.distinct_count) })
    rows.push({ label: 'null_count', value: String(stats.null_count) })
  }
  rows.push({ label: 'CRC32', value: sel.payload_crc32 })
  return rows
})

const candidateRows = computed(() => {
  const cands = preview.value?.candidates ?? []
  return cands.map((c) => ({
    encoding: c.encoding,
    encoded_bytes: c.encoded_bytes,
    raw_bytes: c.raw_bytes,
    gain: c.gain,
    encode_ns: c.encode_ns,
    selected: c.selected,
    reason: c.reason,
  }))
})

const decisionRows = computed(() => {
  const rows: Array<{ label: string; value: string }> = [
    { label: '最终选择', value: winnerEncoding.value },
  ]
  const dict = preview.value?.dictionary
  if (dict) {
    rows.push({ label: '编码宽度', value: `uint${dict.bit_width}` })
    rows.push({ label: '字典项', value: String(dict.dictionary_count) })
  }
  if (preview.value?.selection_reason) {
    rows.push({ label: '选择依据', value: codecReasonLabel(preview.value.selection_reason) })
  } else if (props.selectedBlock?.prune_reason) {
    rows.push({ label: '选择依据', value: props.selectedBlock.prune_reason })
  }
  if (props.selectedBlock?.prune_state) {
    rows.push({ label: '裁剪状态', value: props.selectedBlock.prune_state })
  }
  return rows
})

const hasStructureDetail = computed(
  () => Boolean(preview.value?.rle_runs?.length || preview.value?.dictionary),
)

async function loadPreview() {
  preview.value = null
  loadError.value = null
  structureOpen.value = false
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
  <aside class="block-inspector workspace-panel">
    <div class="panel-header">
      <span class="panel-title">块检查器</span>
      <button type="button" class="collapse-btn" title="折叠面板" @click="layoutStore.toggleRight()">
        <ChevronRight :size="16" :stroke-width="1.5" />
      </button>
    </div>

    <div class="panel-body">
      <p v-if="!selectedBlock" class="hint">点击列块轨道中的块查看编码结论与结构摘要。</p>
      <p v-else-if="loading" class="hint">加载块预览…</p>
      <p v-else-if="loadError" class="hint error">{{ loadError }}</p>

      <template v-else-if="selectedBlock">
        <div class="block-identity">{{ blockLabel }}</div>

        <BlockMetadataGrid :rows="metadataRows" />

        <CodecCompetitionTable v-if="candidateRows.length" :rows="candidateRows" />

        <FinalCodecDecision v-if="decisionRows.length" :rows="decisionRows" />

        <section v-if="hasStructureDetail" class="structure-fold">
          <button type="button" class="fold-toggle" @click="structureOpen = !structureOpen">
            <ChevronDown v-if="structureOpen" :size="14" />
            <ChevronRight v-else :size="14" />
            编码结构详情
          </button>
          <div v-if="structureOpen" class="fold-body">
            <div v-if="preview?.rle_runs?.length">
              <div class="sub-title">RLE 游程</div>
              <RleRunPreview :runs="preview.rle_runs" />
            </div>
            <div v-if="preview?.dictionary">
              <div class="sub-title">Dictionary</div>
              <DictionaryPreview :dictionary="preview.dictionary" />
            </div>
          </div>
        </section>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.block-inspector {
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: var(--workspace-panel-header-height);
  min-height: var(--workspace-panel-header-height);
  padding: 0 12px;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-raised);
  flex-shrink: 0;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  color: var(--text-secondary);
  cursor: pointer;
}

.panel-body {
  flex: 1;
  overflow: auto;
  overflow-x: hidden;
  padding: 10px 12px;
  min-height: 0;
  min-width: 0;
}

.hint {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
}

.hint.error {
  color: var(--danger);
}

.block-identity {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.structure-fold {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.fold-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 4px 0;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  text-align: left;
}

.fold-body {
  margin-top: 8px;
}

.sub-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 8px 0 4px;
}
</style>
