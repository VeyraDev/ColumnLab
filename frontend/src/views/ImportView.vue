<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ImportPipeline from '@/components/import-progress/ImportPipeline.vue'
import PageBackNav from '@/components/workspace/PageBackNav.vue'
import { previewSchema, type SchemaColumnPreview } from '@/api/import'
import { useDatasetStore } from '@/stores/dataset'
import { useImportJobStore } from '@/stores/importJob'

const router = useRouter()
const importStore = useImportJobStore()
const datasetStore = useDatasetStore()

const LOGICAL_TYPES = ['INT64', 'FLOAT64', 'BOOLEAN', 'UTF8', 'DATE32', 'TIMESTAMP64', 'DECIMAL64']

const file = ref<File | null>(null)
const importMode = ref<'strict' | 'coerce'>('strict')
const tableName = ref('data')
const targetBlockBytes = ref(65536)
const demoDenseBlocks = ref(false)
const schemaColumns = ref<SchemaColumnPreview[]>([])
const schemaLoading = ref(false)
const schemaError = ref('')

const blockSizeOptions = [
  { label: '16 KiB', value: 16384 },
  { label: '32 KiB', value: 32768 },
  { label: '64 KiB（默认）', value: 65536 },
  { label: '128 KiB', value: 131072 },
  { label: '256 KiB', value: 262144 },
  { label: '4 KiB（演示密集块）', value: 4096 },
]

async function onFileChange(event: Event) {
  const picked = (event.target as HTMLInputElement).files?.[0] ?? null
  file.value = picked
  schemaColumns.value = []
  schemaError.value = ''
  if (!picked) return
  schemaLoading.value = true
  try {
    const preview = await previewSchema(picked)
    schemaColumns.value = preview.columns.map((col) => ({ ...col }))
  } catch (err) {
    schemaError.value = err instanceof Error ? err.message : '无法推断列类型'
  } finally {
    schemaLoading.value = false
  }
}

function buildSchemaOverrides() {
  return JSON.stringify(
    schemaColumns.value.map((col) => ({
      name: col.name,
      logical_type: col.logical_type,
      scale: col.logical_type === 'DECIMAL64' ? col.scale : 0,
      nullable: col.nullable,
    })),
  )
}

async function onSubmit() {
  if (!file.value) return
  const blockBytes = demoDenseBlocks.value ? 4096 : targetBlockBytes.value
  const result = await importStore.upload(file.value, {
    importMode: importMode.value,
    tableName: tableName.value,
    targetBlockBytes: blockBytes,
    schemaOverrides: schemaColumns.value.length ? buildSchemaOverrides() : '[]',
  })
  watchJob(result.job_id, result.dataset_id)
}

function watchJob(jobId: number, datasetId: number) {
  const stop = watch(
    () => importStore.currentJob?.status,
    (status) => {
      if (status === 'completed') {
        stop()
        void datasetStore.fetchDatasets()
        void router.push(`/workspace/${datasetId}`)
      }
    },
  )
}

async function onCancel() {
  if (importStore.currentJob) {
    await importStore.cancel(importStore.currentJob.id)
  }
}

function openDataset(id: number) {
  void router.push(`/workspace/${id}`)
}

async function onDeleteDataset(id: number, name: string) {
  const ok = window.confirm(`确定删除数据集「${name}」？\n\n将移除该数据集及其表结构与列块数据，且不可恢复。`)
  if (!ok) return
  try {
    await datasetStore.removeDataset(id)
    const cur = router.currentRoute.value
    if (cur.name === 'workspace' && Number(cur.params.datasetId) === id) {
      await router.replace('/imports')
    }
  } catch {
    /* 错误已由 request 拦截器提示 */
  }
}

onMounted(() => {
  void datasetStore.fetchDatasets()
})

onUnmounted(() => importStore.stopTracking())
</script>

<template>
  <div class="import-view">
    <PageBackNav />
    <header class="page-header">
      <h1>导入数据</h1>
      <p>上传 CSV 或 XLSX，确认列类型后写入列式存储。</p>
    </header>
    <form class="import-form" @submit.prevent="onSubmit">
      <label class="field">
        <span>数据文件</span>
        <input type="file" accept=".csv,.xlsx" @change="onFileChange" />
      </label>
      <label class="field">
        <span>表名</span>
        <input v-model="tableName" type="text" />
      </label>

      <section v-if="schemaLoading" class="schema-panel">
        <p class="state-hint">正在推断列类型…</p>
      </section>
      <section v-else-if="schemaError" class="schema-panel">
        <p class="state-hint error">{{ schemaError }}</p>
      </section>
      <section v-else-if="schemaColumns.length" class="schema-panel">
        <div class="schema-header">
          <span class="schema-title">列类型确认</span>
          <span class="schema-meta">可覆盖推断结果</span>
        </div>
        <table class="schema-table">
          <thead>
            <tr>
              <th>列名</th>
              <th>逻辑类型</th>
              <th>可空</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="col in schemaColumns" :key="col.name">
              <td class="mono">{{ col.name }}</td>
              <td>
                <select v-model="col.logical_type">
                  <option v-for="t in LOGICAL_TYPES" :key="t" :value="t">{{ t }}</option>
                </select>
              </td>
              <td>
                <input v-model="col.nullable" type="checkbox" />
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <label class="field">
        <span>块大小</span>
        <select v-model.number="targetBlockBytes" :disabled="demoDenseBlocks">
          <option v-for="opt in blockSizeOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </label>
      <label class="field checkbox-field">
        <input v-model="demoDenseBlocks" type="checkbox" />
        <span>演示密集块模式（4 KiB，产生更多小块便于展示）</span>
      </label>
      <label class="field">
        <span>导入模式</span>
        <select v-model="importMode">
          <option value="strict">严格（类型错误即失败）</option>
          <option value="coerce">宽松（无效值转 NULL）</option>
        </select>
      </label>
      <div class="actions">
        <button
          type="submit"
          class="btn-primary"
          :disabled="!file || importStore.uploading || schemaLoading"
        >
          {{ importStore.uploading ? '上传中…' : '开始导入' }}
        </button>
        <button
          v-if="importStore.currentJob && !['completed', 'failed', 'cancelled'].includes(importStore.currentJob.status)"
          type="button"
          class="btn-ghost"
          @click="onCancel"
        >
          取消任务
        </button>
      </div>
    </form>
    <ImportPipeline :job="importStore.currentJob" />

    <section class="dataset-panel">
      <div class="dataset-header">
        <span class="dataset-title">已导入数据集</span>
        <button type="button" class="btn-ghost" :disabled="datasetStore.loading" @click="datasetStore.fetchDatasets()">
          {{ datasetStore.loading ? '刷新中…' : '刷新' }}
        </button>
      </div>
      <p v-if="datasetStore.loading && !datasetStore.datasets.length" class="state-hint">加载数据集…</p>
      <p v-else-if="!datasetStore.datasets.length" class="state-hint">暂无已就绪的数据集。完成导入后将显示在此。</p>
      <table v-else class="dataset-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>源文件</th>
            <th>行数</th>
            <th>表数</th>
            <th class="th-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ds in datasetStore.datasets" :key="ds.id">
            <td class="mono">{{ ds.name }}</td>
            <td class="source-file" :title="ds.source_file_name">{{ ds.source_file_name || '—' }}</td>
            <td class="mono">{{ ds.row_count.toLocaleString() }}</td>
            <td class="mono">{{ ds.table_count }}</td>
            <td class="td-actions">
              <button type="button" class="btn-link" @click="openDataset(ds.id)">打开</button>
              <button
                type="button"
                class="btn-link danger"
                :disabled="datasetStore.deletingId === ds.id"
                @click="onDeleteDataset(ds.id, ds.name)"
              >
                {{ datasetStore.deletingId === ds.id ? '删除中…' : '删除' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.import-view {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px;
}

.page-header h1 {
  margin: 0 0 6px;
  font-size: 18px;
}

.page-header p {
  margin: 0 0 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.import-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.field input,
.field select {
  height: 32px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  padding: 0 8px;
  background: var(--bg-panel);
}

.schema-panel {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  padding: 10px;
  background: var(--bg-panel);
}

.schema-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}

.schema-title {
  font-size: 12px;
  font-weight: 600;
}

.schema-meta {
  font-size: 11px;
  color: var(--text-tertiary);
}

.schema-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.schema-table th,
.schema-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-default);
  text-align: left;
}

.schema-table select {
  width: 100%;
  height: 28px;
}

.mono {
  font-family: var(--font-mono);
}

.state-hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.state-hint.error {
  color: #b91c1c;
}

.checkbox-field {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.checkbox-field input {
  width: auto;
  height: auto;
}

.actions {
  display: flex;
  gap: 8px;
}

.btn-primary,
.btn-ghost {
  height: 32px;
  padding: 0 12px;
  border-radius: var(--radius-control);
  font-size: 12px;
  cursor: pointer;
  border: 1px solid var(--border-default);
}

.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.btn-ghost {
  background: var(--bg-panel);
  color: var(--text-secondary);
}

.btn-link {
  border: none;
  background: transparent;
  padding: 0;
  font-size: 12px;
  color: var(--accent);
  cursor: pointer;
}

.btn-link:hover {
  color: var(--accent-hover);
  text-decoration: underline;
}

.btn-link:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  text-decoration: none;
}

.btn-link.danger {
  color: var(--danger);
}

.dataset-panel {
  margin-top: 24px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  padding: 10px;
  background: var(--bg-panel);
}

.dataset-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.dataset-title {
  font-size: 12px;
  font-weight: 600;
}

.dataset-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.dataset-table th,
.dataset-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-default);
  text-align: left;
}

.dataset-table tr:last-child td {
  border-bottom: none;
}

.th-actions,
.td-actions {
  width: 120px;
  white-space: nowrap;
}

.td-actions {
  display: flex;
  gap: 10px;
}

.source-file {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
</style>
