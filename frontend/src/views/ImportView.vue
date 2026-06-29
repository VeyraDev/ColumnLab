<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ImportPipeline from '@/components/import-progress/ImportPipeline.vue'
import PageBackNav from '@/components/workspace/PageBackNav.vue'
import { useImportJobStore } from '@/stores/importJob'

const router = useRouter()
const importStore = useImportJobStore()

const file = ref<File | null>(null)
const importMode = ref<'strict' | 'coerce'>('strict')
const tableName = ref('data')

async function onSubmit() {
  if (!file.value) return
  const result = await importStore.upload(file.value, {
    importMode: importMode.value,
    tableName: tableName.value,
    targetBlockBytes: 4096,
  })
  watchJob(result.job_id, result.dataset_id)
}

function watchJob(jobId: number, datasetId: number) {
  const stop = watch(
    () => importStore.currentJob?.status,
    (status) => {
      if (status === 'completed') {
        stop()
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

onUnmounted(() => importStore.stopPolling())
</script>

<template>
  <div class="import-view">
    <PageBackNav />
    <header class="page-header">
      <h1>导入数据</h1>
      <p>上传 CSV 或 XLSX，系统将流式解析并写入列式存储。</p>
    </header>
    <form class="import-form" @submit.prevent="onSubmit">
      <label class="field">
        <span>数据文件</span>
        <input type="file" accept=".csv,.xlsx" @change="(e) => (file = (e.target as HTMLInputElement).files?.[0] ?? null)" />
      </label>
      <label class="field">
        <span>表名</span>
        <input v-model="tableName" type="text" />
      </label>
      <label class="field">
        <span>导入模式</span>
        <select v-model="importMode">
          <option value="strict">严格（类型错误即失败）</option>
          <option value="coerce">宽松（无效值转 NULL）</option>
        </select>
      </label>
      <div class="actions">
        <button type="submit" class="btn-primary" :disabled="!file || importStore.uploading">
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
</style>
