<script setup lang="ts">
import { computed } from 'vue'
import type { BenchmarkRun } from '@/api/benchmarks'
import { buildCodecConclusion } from '@/utils/benchmarkAnalysis'
import type { MetricStats } from '@/api/benchmarks'

const props = defineProps<{
  run: BenchmarkRun | null
  analysisColumn: string
  metrics: Record<string, MetricStats>
}>()

const conclusion = computed(() => {
  if (!props.run?.config || !props.run.summary) {
    return { headline: '尚未完成实验', detail: '', takeaway: '', meta: [] as string[] }
  }
  return buildCodecConclusion(props.run.config, props.metrics, props.analysisColumn)
})
</script>

<template>
  <section class="conclusion">
    <h2>{{ conclusion.headline }}</h2>
    <p v-if="conclusion.detail" class="detail">{{ conclusion.detail }}</p>
    <p v-if="conclusion.takeaway" class="takeaway">{{ conclusion.takeaway }}</p>
    <ul v-if="conclusion.meta.length" class="meta">
      <li v-for="(line, i) in conclusion.meta" :key="i">{{ line }}</li>
    </ul>
  </section>
</template>

<style scoped>
.conclusion {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 12px 14px;
  background: var(--bg-raised);
}

h2 {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
}

.detail,
.takeaway {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-primary);
}

.takeaway {
  font-weight: 600;
}

.meta {
  margin: 0;
  padding-left: 0;
  list-style: none;
  font-size: 11px;
  color: var(--text-tertiary);
}

.meta li + li {
  margin-top: 2px;
}
</style>
