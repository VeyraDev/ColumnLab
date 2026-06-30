<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
import { useWorkspaceLayoutStore } from '@/stores/workspaceLayoutStore'
import RleRunPreview from './RleRunPreview.vue'
import DictionaryPreview from './DictionaryPreview.vue'
import { getBlockPreview, type BlockPreview } from '@/api/datasets'
import { formatBlockLabel, formatBytes } from '@/utils/format'
import type { SelectedBlockMeta } from '@/stores/storageMapStore'

const props = defineProps<{
  selectedBlock?: SelectedBlockMeta | null
}>()

const layoutStore = useWorkspaceLayoutStore()
const activeTab = ref<'meta' | 'structure' | 'pruning'>('meta')

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

const savingsPct = computed(() => {
  if (!rawBytes.value) return '—'
  return `${((1 - encodedBytes.value / rawBytes.value) * 100).toFixed(1)}%`
})

const ratioPct = computed(() => {
  if (!rawBytes.value) return 0
  return Math.min(100, Math.round((encodedBytes.value / rawBytes.value) * 100))
})

const candidateRows = computed(() => {
  const cands = preview.value?.candidates ?? []
  if (!cands.length) return []
  const baseline =
    cands.find((c) => c.encoding.toUpperCase() === 'RAW')?.encoded_bytes ?? cands[0].encoded_bytes
  return cands.map((c) => {
    let status = '—'
    if (c.selected) status = '已选'
    else if (c.encoding.toUpperCase() === 'RAW') status = '基准'
    else if (baseline > 0) {
      const delta = ((c.encoded_bytes / baseline - 1) * 100).toFixed(1)
      status = `${Number(delta) >= 0 ? '+' : ''}${delta}%`
    }
    return {
      encoding: c.encoding,
      label: formatBytes(c.encoded_bytes),
      status,
      selected: c.selected,
    }
  })
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

async function loadPreview() {
  preview.value = null
  loadError.value = null
  activeTab.value = 'meta'
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
      <span class="panel-title">块检查器</span>
      <button type="button" class="collapse-btn" title="折叠面板" @click="layoutStore.toggleRight()">
        <ChevronRight :size="14" :stroke-width="1.5" />
      </button>
    </div>

    <div class="panel-body">
      <p v-if="!selectedBlock" class="hint">点击列块轨道中的块查看编码结论与结构摘要。</p>
      <p v-else-if="loading" class="hint">加载块预览…</p>
      <p v-else-if="loadError" class="hint error">{{ loadError }}</p>

      <template v-else-if="selectedBlock && block">
        <!-- 结论区 -->
        <section class="conclusion-zone">
          <div class="block-id">{{ blockLabel }}</div>
          <div class="encoding-name">{{ winnerEncoding }}</div>
          <div class="size-line mono">
            {{ formatBytes(encodedBytes) }} / {{ formatBytes(rawBytes) }}
          </div>
          <div class="savings-line">节省 {{ savingsPct }}</div>
          <div class="ratio-track" aria-hidden="true">
            <div class="ratio-fill" :style="{ width: `${ratioPct}%` }" />
          </div>
        </section>

        <!-- 候选比较区 -->
        <section v-if="candidateRows.length" class="candidate-zone">
          <table class="candidate-table">
            <thead>
              <tr>
                <th>编码</th>
                <th>大小</th>
                <th>差异</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in candidateRows"
                :key="row.encoding"
                :class="{ selected: row.selected }"
              >
                <td class="cand-encoding">{{ row.encoding }}</td>
                <td class="cand-size mono">{{ row.label }}</td>
                <td class="cand-status">{{ row.status }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <!-- 页签区 -->
        <section class="detail-zone">
          <div class="tab-bar" role="tablist">
            <button
              type="button"
              role="tab"
              :class="{ active: activeTab === 'meta' }"
              @click="activeTab = 'meta'"
            >
              元数据
            </button>
            <button
              type="button"
              role="tab"
              :class="{ active: activeTab === 'structure' }"
              @click="activeTab = 'structure'"
            >
              编码结构
            </button>
            <button
              type="button"
              role="tab"
              :class="{ active: activeTab === 'pruning' }"
              @click="activeTab = 'pruning'"
            >
              裁剪依据
            </button>
          </div>

          <div class="tab-panel">
            <dl v-if="activeTab === 'meta'" class="meta-list">
              <div><dt>起始行</dt><dd class="mono">{{ block.row_start.toLocaleString() }}</dd></div>
              <div><dt>行数</dt><dd class="mono">{{ block.row_count.toLocaleString() }}</dd></div>
              <div v-if="preview?.stats?.min_repr"><dt>min</dt><dd class="mono">{{ preview.stats.min_repr }}</dd></div>
              <div v-if="preview?.stats?.max_repr"><dt>max</dt><dd class="mono">{{ preview.stats.max_repr }}</dd></div>
              <div v-if="preview?.stats"><dt>NULL</dt><dd class="mono">{{ preview.stats.null_count }}</dd></div>
              <div v-if="preview?.stats"><dt>distinct</dt><dd class="mono">{{ preview.stats.distinct_count }}</dd></div>
              <div><dt>CRC32</dt><dd class="mono">{{ block.crc32 }}</dd></div>
            </dl>

            <div v-else-if="activeTab === 'structure'" class="structure-panel">
              <p v-if="!preview?.rle_runs?.length && !preview?.dictionary" class="hint">
                当前块无 RLE / Dictionary 结构摘要。
              </p>
              <div v-if="preview?.rle_runs?.length">
                <div class="sub-title">RLE 游程</div>
                <RleRunPreview :runs="preview.rle_runs" />
              </div>
              <div v-if="preview?.dictionary">
                <div class="sub-title">Dictionary</div>
                <DictionaryPreview :dictionary="preview.dictionary" />
              </div>
            </div>

            <div v-else class="pruning-panel">
              <dl class="meta-list">
                <div v-if="selectedBlock.prune_state">
                  <dt>裁剪状态</dt><dd class="mono">{{ selectedBlock.prune_state }}</dd>
                </div>
                <div v-if="selectedBlock.prune_reason">
                  <dt>跳过理由</dt><dd class="mono">{{ selectedBlock.prune_reason }}</dd>
                </div>
                <div v-if="preview?.selection_reason">
                  <dt>编码选择</dt><dd class="mono">{{ preview.selection_reason }}</dd>
                </div>
              </dl>
              <p v-if="!selectedBlock.prune_state && !preview?.selection_reason" class="hint">
                暂无裁剪或选择依据。
              </p>
            </div>
          </div>
        </section>
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
  min-width: 0;
  overflow-x: hidden;
  background: var(--bg-panel);
  border-left: 1px solid var(--border-default);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: var(--workspace-panel-header-height);
  min-height: var(--workspace-panel-header-height);
  padding: 0 10px;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-raised);
  flex-shrink: 0;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  color: var(--text-tertiary);
  cursor: pointer;
}

.panel-body {
  flex: 1;
  overflow: auto;
  overflow-x: hidden;
  padding: 8px 10px;
  min-height: 0;
  min-width: 0;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.5;
}

.hint.error {
  color: #6b7280;
}

.conclusion-zone {
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-default);
}

.block-id {
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.encoding-name {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--text-primary);
  line-height: 1.25;
}

.size-line {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-primary);
}

.savings-line {
  margin-top: 2px;
  font-size: 11px;
  color: var(--text-secondary);
}

.ratio-track {
  margin-top: 8px;
  height: 3px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.ratio-fill {
  height: 100%;
  background: #374151;
  border-radius: 2px;
}

.candidate-zone {
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-default);
  min-width: 0;
  overflow-x: hidden;
}

.candidate-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  table-layout: fixed;
}

.candidate-table th {
  padding: 2px 4px;
  text-align: left;
  font-weight: 500;
  color: var(--text-tertiary);
  border-bottom: 1px solid var(--border-default);
}

.candidate-table th:nth-child(1) {
  width: 52px;
}

.candidate-table th:nth-child(2) {
  width: 64px;
  text-align: right;
}

.candidate-table th:nth-child(3) {
  width: auto;
}

.candidate-table td {
  padding: 3px 4px;
  border-bottom: 1px solid var(--border-subtle, var(--border-default));
  vertical-align: middle;
}

.candidate-table tr.selected {
  background: var(--state-active-bg);
  box-shadow: inset 2px 0 0 var(--state-active-border);
}

.cand-encoding {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}

.candidate-table tr.selected .cand-encoding {
  font-weight: 600;
  color: var(--text-primary);
}

.cand-size {
  text-align: right;
  color: var(--text-primary);
  white-space: nowrap;
}

.cand-status {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-tertiary);
  font-size: 10px;
}

.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-default);
  margin-bottom: 8px;
}

.tab-bar button {
  flex: 1;
  padding: 5px 4px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  font-size: 11px;
  color: var(--text-tertiary);
  cursor: pointer;
}

.tab-bar button.active {
  color: var(--text-primary);
  font-weight: 600;
  border-bottom-color: #374151;
}

.meta-list {
  margin: 0;
}

.meta-list div {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 8px;
  padding: 3px 0;
  font-size: 11px;
}

.meta-list dt {
  color: var(--text-tertiary);
}

.meta-list dd {
  margin: 0;
  color: var(--text-primary);
  word-break: break-word;
}

.sub-title {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 8px 0 4px;
}

.structure-panel > div:first-child .sub-title {
  margin-top: 0;
}
</style>
