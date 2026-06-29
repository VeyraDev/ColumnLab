<script setup lang="ts">
import type { BenchmarkConfig } from '@/api/benchmarks'

const config = defineModel<BenchmarkConfig>('config', { required: true })
const loading = defineProps<{ loading?: boolean }>()

const distributions = [
  { value: 'run_length', label: '游程 (run_length)' },
  { value: 'low_cardinality', label: '低基数 (low_cardinality)' },
  { value: 'high_cardinality', label: '高基数 (high_cardinality)' },
  { value: 'uniform', label: '均匀 (uniform)' },
  { value: 'skewed', label: '偏斜 (skewed)' },
  { value: 'with_null', label: '含 NULL (with_null)' },
  { value: 'mixed_business', label: '混合业务 (mixed_business)' },
]
</script>

<template>
  <section class="configurator">
    <h2>实验参数</h2>
    <div class="grid">
      <label>
        类型
        <select v-model="config.kind">
          <option value="codec">Codec 基准</option>
          <option value="query">Query 基准</option>
        </select>
      </label>
      <label>
        随机种子
        <input v-model.number="config.seed" type="number" min="0" />
      </label>
      <label>
        预热次数
        <input v-model.number="config.warmup_runs" type="number" min="0" max="10" />
      </label>
      <label>
        重复次数
        <input v-model.number="config.repeat_runs" type="number" min="1" max="20" />
      </label>
      <label>
        数据分布
        <select v-model="config.distribution">
          <option v-for="d in distributions" :key="d.value" :value="d.value">{{ d.label }}</option>
        </select>
      </label>
      <label>
        行数
        <input v-model.number="config.row_count" type="number" min="256" step="256" />
      </label>
      <label>
        缓存模式
        <select v-model="config.cache_mode">
          <option value="cold">冷缓存</option>
          <option value="hot">热缓存</option>
        </select>
      </label>
      <label class="checkbox">
        <input v-model="config.pruning_enabled" type="checkbox" />
        启用块裁剪
      </label>
    </div>
    <div v-if="config.kind === 'query'" class="query-extra">
      <label>
        数据集 ID
        <input v-model.number="config.dataset_id" type="number" min="1" placeholder="可选" />
      </label>
      <label class="wide">
        SQL
        <input v-model="config.sql" type="text" placeholder="SELECT COUNT(*) FROM data" />
      </label>
    </div>
    <slot />
  </section>
</template>

<style scoped>
.configurator {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-panel);
  padding: 12px 14px;
  background: var(--bg-panel);
}

h2 {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

label.checkbox {
  flex-direction: row;
  align-items: center;
  gap: 6px;
  padding-top: 18px;
}

input,
select {
  font-size: 12px;
  padding: 4px 6px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-app);
  color: var(--text-primary);
}

.query-extra {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 10px;
}

.wide {
  grid-column: span 1;
}
</style>
