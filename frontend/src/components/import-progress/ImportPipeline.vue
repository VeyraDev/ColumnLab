<script setup lang="ts">
import type { ImportJobState } from '@/api/import'

defineProps<{
  job: ImportJobState | null
}>()

const stages = [
  'pending',
  'parsing',
  'inferring',
  'partitioning',
  'encoding',
  'writing',
  'validating',
  'committing',
  'completed',
]
</script>

<template>
  <section class="import-pipeline">
    <div class="pipeline-header">导入进度</div>
    <div v-if="!job" class="empty">选择文件并开始上传</div>
    <template v-else>
      <dl class="metrics">
        <div><dt>阶段</dt><dd class="mono">{{ job.stage }}</dd></div>
        <div><dt>状态</dt><dd>{{ job.status }}</dd></div>
        <div><dt>已处理行</dt><dd class="mono">{{ job.rows_processed }}</dd></div>
        <div><dt>已处理字节</dt><dd class="mono">{{ job.bytes_processed }}</dd></div>
        <div><dt>当前列</dt><dd class="mono">{{ job.current_column || '—' }}</dd></div>
        <div><dt>错误数</dt><dd class="mono">{{ job.error_count }}</dd></div>
      </dl>
      <ol class="stage-list">
        <li
          v-for="stage in stages"
          :key="stage"
          :class="{ active: job.stage === stage, done: stages.indexOf(job.stage) > stages.indexOf(stage) }"
        >
          {{ stage }}
        </li>
      </ol>
      <p v-if="job.error_message" class="error">{{ job.error_message }}</p>
      <ul v-if="job.error_samples?.length" class="error-samples">
        <li v-for="(sample, idx) in job.error_samples" :key="idx">
          行 {{ sample.row }} · {{ sample.column }} · {{ sample.value }} — {{ sample.reason }}
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.import-pipeline {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  background: var(--bg-panel);
  padding: 12px;
}

.pipeline-header {
  font-weight: 600;
  font-size: 12px;
  margin-bottom: 10px;
}

.empty {
  color: var(--text-tertiary);
  font-size: 12px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 12px;
}

.metrics div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
}

.metrics dt {
  color: var(--text-tertiary);
}

.metrics dd {
  margin: 0;
  color: var(--text-primary);
}

.stage-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.stage-list li {
  font-size: 10px;
  padding: 2px 6px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  color: var(--text-tertiary);
}

.stage-list li.active {
  border-color: var(--accent);
  color: var(--accent);
}

.stage-list li.done {
  color: var(--text-secondary);
}

.error {
  margin: 10px 0 0;
  color: var(--danger);
  font-size: 12px;
}

.error-samples {
  margin: 8px 0 0;
  padding-left: 16px;
  font-size: 11px;
  color: var(--text-secondary);
}
</style>
