<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useDatasetStore } from '@/stores/dataset'
import { useQueryStore } from '@/stores/query'

const props = defineProps<{
  datasetId?: string
}>()

const userStore = useUserStore()
const datasetStore = useDatasetStore()
const queryStore = useQueryStore()
const router = useRouter()
const searchRef = ref<HTMLInputElement | null>(null)

const canRunQuery = computed(() => Boolean(props.datasetId) && !queryStore.loading)

const selectedId = computed({
  get: () => props.datasetId ?? '',
  set: (value: string) => {
    if (value) router.push(`/workspace/${value}`)
  },
})

onMounted(() => {
  void datasetStore.fetchDatasets()
  window.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
})

watch(
  () => props.datasetId,
  () => {
    void datasetStore.fetchDatasets()
  },
)

function onGlobalKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    searchRef.value?.focus()
  }
}

function goImport() {
  router.push('/imports')
}

async function runQuery() {
  if (!props.datasetId) return
  await queryStore.runQuery(Number(props.datasetId))
}

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <header class="top-bar">
    <div class="brand">
      <span class="brand-title">ColumnLab</span>
      <span class="brand-sub">列式存储引擎观测台</span>
    </div>
    <div class="top-center">
      <select v-model="selectedId" class="dataset-select">
        <option value="">未选择数据集</option>
        <option v-for="ds in datasetStore.datasets" :key="ds.id" :value="String(ds.id)">
          {{ ds.name }} ({{ ds.row_count }} 行)
        </option>
      </select>
      <div class="search-wrap">
        <span class="search-icon" aria-hidden="true">⌕</span>
        <input
          ref="searchRef"
          class="search-input"
          type="search"
          placeholder="搜索表、列或过滤条件 (Ctrl+K)"
          disabled
        />
      </div>
    </div>
    <div class="top-actions">
      <button type="button" class="btn-ghost" @click="goImport">导入数据</button>
      <button type="button" class="btn-primary" :disabled="!canRunQuery" @click="runQuery">
        <span class="play-icon" aria-hidden="true">▶</span>
        运行查询
      </button>
      <span class="user-label">{{ userStore.user?.username }}</span>
      <button type="button" class="btn-ghost" @click="logout">退出</button>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  display: grid;
  grid-template-columns: minmax(160px, 200px) minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 6px 12px;
  background: var(--bg-raised);
  border-bottom: 1px solid var(--border-default);
  min-height: 44px;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.brand-title {
  font-weight: 600;
  font-size: 14px;
  line-height: 1.2;
}

.brand-sub {
  font-size: 10px;
  color: var(--text-tertiary);
  line-height: 1.2;
}

.top-center {
  display: flex;
  gap: 8px;
  min-width: 0;
}

.dataset-select,
.search-input {
  height: 28px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  padding: 0 8px;
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 0;
}

.dataset-select {
  width: 168px;
  flex-shrink: 0;
}

.search-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  padding: 0 8px;
  height: 28px;
}

.search-icon {
  color: var(--text-tertiary);
  font-size: 13px;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0;
  height: auto;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-ghost,
.btn-primary {
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-control);
  font-size: 12px;
  cursor: pointer;
  border: 1px solid var(--border-default);
  background: var(--bg-panel);
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.play-icon {
  font-size: 10px;
}

.user-label {
  font-size: 12px;
  color: var(--text-secondary);
  padding-left: 2px;
}
</style>
