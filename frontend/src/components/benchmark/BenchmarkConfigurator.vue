<script setup lang="ts">
import type { BenchmarkConfig } from '@/api/benchmarks'

const config = defineModel<BenchmarkConfig>('config', { required: true })

const distributions = [
  { value: 'run_length', label: '游程' },
  { value: 'low_cardinality', label: '低基数' },
  { value: 'high_cardinality', label: '高基数' },
  { value: 'uniform', label: '均匀' },
  { value: 'skewed', label: '偏斜' },
  { value: 'with_null', label: '含 NULL' },
  { value: 'mixed_business', label: '混合业务' },
]

const blockSizeOptions = [4096, 16384, 65536]
</script>

<template>
  <section class="configurator">
    <h2>实验配置</h2>

    <label>
      实验类型
      <select v-model="config.kind">
        <option value="codec">Codec 基准</option>
        <option value="query">Query 基准</option>
      </select>
    </label>

    <label>
      数据集 ID
      <input
        v-model.number="config.dataset_id"
        type="number"
        min="1"
        placeholder="Query 实验"
        :disabled="config.kind !== 'query'"
      />
    </label>

    <label>
      块大小
      <select
        :value="config.block_sizes?.[0] ?? 65536"
        @change="config.block_sizes = [Number(($event.target as HTMLSelectElement).value)]"
      >
        <option v-for="bs in blockSizeOptions" :key="bs" :value="bs">{{ bs }} B</option>
      </select>
    </label>

    <label>
      缓存模式
      <select v-model="config.cache_mode">
        <option value="cold">冷缓存</option>
        <option value="hot">热缓存</option>
      </select>
    </label>

    <label>
      预热次数
      <input v-model.number="config.warmup_runs" type="number" min="0" max="10" />
    </label>

    <label>
      重复次数
      <input v-model.number="config.repeat_runs" type="number" min="1" max="20" />
    </label>

    <template v-if="config.kind === 'codec'">
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
    </template>

    <label v-if="config.kind === 'query'" class="wide">
      SQL
      <input v-model="config.sql" type="text" placeholder="SELECT COUNT(*) FROM data" />
    </label>

    <label class="checkbox">
      <input v-model="config.pruning_enabled" type="checkbox" />
      启用块裁剪
    </label>

    <label>
      随机种子
      <input v-model.number="config.seed" type="number" min="0" />
    </label>

    <slot />
  </section>
</template>

<style scoped>
.configurator {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  overflow: auto;
}

h2 {
  margin: 0 0 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
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
}

input,
select {
  font-size: 12px;
  padding: 5px 8px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-app);
  color: var(--text-primary);
  width: 100%;
}

input:disabled {
  opacity: 0.5;
}
</style>
