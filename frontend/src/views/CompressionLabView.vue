<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { listColumns, listTables } from '@/api/datasets'
import { getBlockPreview, type BlockPreview } from '@/api/datasets'
import CodecCandidateTable from '@/components/block-inspector/CodecCandidateTable.vue'
import RleRunPreview from '@/components/block-inspector/RleRunPreview.vue'
import DictionaryPreview from '@/components/block-inspector/DictionaryPreview.vue'
import EncodingLegend from '@/components/block-inspector/EncodingLegend.vue'
import PageBackNav from '@/components/workspace/PageBackNav.vue'

const route = useRoute()
const datasetId = computed(() => route.params.datasetId as string | undefined)

const columns = ref<Array<{ id: number; name: string; logical_type: string }>>([])
const selectedColumnId = ref<number | null>(null)
const blockId = ref(0)
const preview = ref<BlockPreview | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function loadColumns() {
  columns.value = []
  preview.value = null
  if (!datasetId.value) return
  const tables = await listTables(Number(datasetId.value))
  if (!tables.length) return
  const cols = await listColumns(tables[0].id)
  columns.value = cols.map((c) => ({ id: c.id, name: c.name, logical_type: c.logical_type }))
  if (cols.length) selectedColumnId.value = cols[0].id
}

async function loadPreview() {
  preview.value = null
  error.value = null
  if (selectedColumnId.value == null) return
  loading.value = true
  try {
    preview.value = await getBlockPreview(selectedColumnId.value, blockId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

watch([selectedColumnId, blockId], loadPreview)
watch(datasetId, loadColumns, { immediate: true })
onMounted(loadColumns)
</script>

<template>
  <div class="compression-lab">
    <PageBackNav :dataset-id="datasetId" label="返回工作区" />
    <header class="lab-header">
      <h1>压缩实验</h1>
      <p class="subtitle">
        选择列与块，查看编码候选与结构摘要。
        <router-link to="/benchmarks" class="bench-link">打开性能基准中心 →</router-link>
      </p>
    </header>
    <div class="lab-controls">
      <label>
        列
        <select v-model.number="selectedColumnId">
          <option v-for="col in columns" :key="col.id" :value="col.id">
            {{ col.name }} ({{ col.logical_type }})
          </option>
        </select>
      </label>
      <label>
        块 ID
        <input v-model.number="blockId" type="number" min="0" />
      </label>
      <button type="button" :disabled="loading" @click="loadPreview">刷新</button>
    </div>
    <p v-if="!datasetId" class="hint">请从工作区选择数据集，或访问 /compression-lab/:datasetId</p>
    <p v-else-if="loading" class="hint">加载中…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>
    <template v-else-if="preview">
      <EncodingLegend />
      <p class="mono reason">{{ preview.selection_reason }} → {{ preview.winner_encoding }}</p>
      <CodecCandidateTable :candidates="preview.candidates" />
      <div v-if="preview.rle_runs?.length" class="section">
        <h2>RLE 游程</h2>
        <RleRunPreview :runs="preview.rle_runs" />
      </div>
      <div v-if="preview.dictionary" class="section">
        <h2>Dictionary</h2>
        <DictionaryPreview :dictionary="preview.dictionary" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.compression-lab {
  padding: 16px 20px;
  max-width: 960px;
  margin: 0 auto;
}

.lab-header h1 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
}

.subtitle {
  margin: 0 0 16px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.bench-link {
  margin-left: 8px;
  color: var(--accent, #2563eb);
  text-decoration: none;
}

.bench-link:hover {
  text-decoration: underline;
}

.lab-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: end;
  margin-bottom: 16px;
  font-size: 12px;
}

.lab-controls label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lab-controls select,
.lab-controls input {
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--border-default);
  background: var(--bg-panel);
}

.lab-controls button {
  height: 28px;
  padding: 0 12px;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
  cursor: pointer;
}

.hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.hint.error {
  color: #b91c1c;
}

.reason {
  font-size: 11px;
  margin: 8px 0;
  color: var(--text-secondary);
}

.section h2 {
  font-size: 12px;
  margin: 16px 0 8px;
}
</style>
