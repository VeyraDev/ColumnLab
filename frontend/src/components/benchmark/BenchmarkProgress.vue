<script setup lang="ts">
import type { BenchmarkEvent } from '@/api/benchmarks'

defineProps<{
  events: BenchmarkEvent[]
  progress: number
  status: string | null
}>()
</script>

<template>
  <section class="progress-panel">
    <div class="bar-track" aria-hidden="true">
      <div class="bar-fill" :style="{ width: `${Math.round(progress * 100)}%` }" />
    </div>
    <p class="status">状态：{{ status ?? '—' }} · 进度 {{ Math.round(progress * 100) }}%</p>
    <ul class="log">
      <li v-for="(ev, i) in events" :key="i">
        <span class="stage">{{ ev.stage }}</span>
        {{ ev.message }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.progress-panel {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 10px 12px;
  background: var(--bg-muted);
}

.bar-track {
  height: 6px;
  background: var(--bg-app);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--state-active-border, #4a6fa5);
  transition: width 0.2s ease;
}

.status {
  margin: 8px 0 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.log {
  margin: 0;
  padding-left: 16px;
  max-height: 120px;
  overflow: auto;
  font-size: 11px;
  color: var(--text-tertiary);
}

.stage {
  font-family: var(--font-mono, monospace);
  color: var(--text-secondary);
  margin-right: 6px;
}
</style>
