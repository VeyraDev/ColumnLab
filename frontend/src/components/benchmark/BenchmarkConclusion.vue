<script setup lang="ts">
import { computed } from 'vue'
import type { BenchmarkRun } from '@/api/benchmarks'

const props = defineProps<{
  run: BenchmarkRun | null
  comparison: Record<string, number>
}>()

const lines = computed(() => {
  const out: string[] = []
  const run = props.run
  if (!run?.summary) return ['尚未完成实验，暂无结论。']

  out.push(
    `实验类型 ${run.summary.kind ?? run.kind}，种子 ${run.summary.seed ?? run.config.seed}，行数 ${run.summary.row_count ?? run.config.row_count}。`,
  )

  const cmp = props.comparison
  if (cmp['qty.rle_vs_raw_bytes_ratio'] != null) {
    const ratio = cmp['qty.rle_vs_raw_bytes_ratio']
    out.push(`qty 列 RLE 相对 RAW 字节比为 ${ratio.toFixed(3)}（小于 1 表示 RLE 更省空间）。`)
  }
  if (cmp['qty.dict_vs_raw_bytes_ratio'] != null) {
    const ratio = cmp['qty.dict_vs_raw_bytes_ratio']
    out.push(`qty 列 DICT 相对 RAW 字节比为 ${ratio.toFixed(3)}。`)
  }
  if (cmp['region.dict_vs_raw_bytes_ratio'] != null) {
    const ratio = cmp['region.dict_vs_raw_bytes_ratio']
    out.push(`region 列 DICT 相对 RAW 字节比为 ${ratio.toFixed(3)}。`)
  }

  if (run.env?.git_commit) {
    out.push(`环境：commit ${run.env.git_commit}，Python ${run.env.python}，CPU ${run.env.cpu_count}。`)
  }

  return out
})
</script>

<template>
  <section class="conclusion">
    <h2>结论摘要</h2>
    <ul>
      <li v-for="(line, i) in lines" :key="i">{{ line }}</li>
    </ul>
    <p class="note">以上仅陈述测量数值与相对关系，不做性能夸大推断。</p>
  </section>
</template>

<style scoped>
.conclusion {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 10px 12px;
  background: var(--bg-muted);
}

h2 {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
}

ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--text-secondary);
}

.note {
  margin: 8px 0 0;
  font-size: 10px;
  color: var(--text-tertiary);
}
</style>
