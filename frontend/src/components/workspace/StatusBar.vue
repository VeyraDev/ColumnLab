<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getDataset } from '@/api/datasets'
import { fetchRuntime, type RuntimeInfo } from '@/api/runtime'
import { formatGiB } from '@/utils/format'

const props = defineProps<{
  datasetId?: string
}>()

const datasetName = ref('')
const storagePath = ref('')
const runtime = ref<RuntimeInfo | null>(null)
const copied = ref(false)

let timer: ReturnType<typeof setInterval> | null = null

async function loadDataset() {
  if (!props.datasetId) {
    datasetName.value = ''
    storagePath.value = ''
    return
  }
  try {
    const ds = await getDataset(Number(props.datasetId))
    datasetName.value = ds.name
    storagePath.value = ds.storage_path ?? ''
  } catch {
    datasetName.value = '—'
    storagePath.value = ''
  }
}

async function loadRuntime() {
  try {
    runtime.value = await fetchRuntime()
  } catch {
    runtime.value = null
  }
}

async function copyPath() {
  if (!storagePath.value) return
  try {
    await navigator.clipboard.writeText(storagePath.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch {
    /* ignore */
  }
}

const memoryPercent = computed(() => {
  if (!runtime.value?.memory_total_bytes) return 0
  return Math.round((runtime.value.memory_used_bytes / runtime.value.memory_total_bytes) * 1000) / 10
})

onMounted(() => {
  void loadDataset()
  void loadRuntime()
  timer = setInterval(() => void loadRuntime(), 30_000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

watch(() => props.datasetId, loadDataset)
</script>

<template>
  <footer class="status-bar">
    <div class="status-left">
      <span>{{ datasetName || '未选择数据集' }}</span>
      <span v-if="runtime" class="mono">v{{ runtime.engine_version }}</span>
      <span v-if="storagePath" class="path mono" :title="storagePath">{{ storagePath }}</span>
      <button
        v-if="storagePath"
        type="button"
        class="copy-btn"
        :title="copied ? '已复制' : '复制路径'"
        @click="copyPath"
      >
        {{ copied ? '✓' : '⧉' }}
      </button>
    </div>
    <div v-if="runtime" class="status-right">
      <span class="mono memory-label">
        {{ formatGiB(runtime.memory_used_bytes) }} / {{ formatGiB(runtime.memory_total_bytes) }}
      </span>
      <div class="memory-bar" aria-hidden="true">
        <div class="memory-fill" :style="{ width: `${memoryPercent}%` }" />
      </div>
      <span class="mono memory-pct">{{ memoryPercent }}%</span>
    </div>
  </footer>
</template>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 12px;
  min-height: 26px;
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-muted);
  border-top: 1px solid var(--border-default);
}

.status-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.path {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 420px;
}

.copy-btn {
  width: 22px;
  height: 20px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  font-size: 11px;
  cursor: pointer;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.status-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.memory-bar {
  width: 80px;
  height: 6px;
  border-radius: 3px;
  background: var(--border-default);
  overflow: hidden;
}

.memory-fill {
  height: 100%;
  background: var(--accent);
}

.memory-label,
.memory-pct {
  white-space: nowrap;
}
</style>
