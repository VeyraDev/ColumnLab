<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { User } from 'lucide-vue-next'
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
const menuOpen = ref(false)

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
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
  document.removeEventListener('click', onDocClick)
})

watch(() => props.datasetId, () => void datasetStore.fetchDatasets())

function onDocClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.user-menu-wrap')) menuOpen.value = false
}

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
  menuOpen.value = false
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
          {{ ds.name }} ({{ ds.row_count.toLocaleString() }} 行)
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
      <button type="button" class="btn-outline" @click="goImport">导入数据</button>
      <button type="button" class="btn-primary" :disabled="!canRunQuery" @click="runQuery">
        <span class="play-icon" aria-hidden="true">▶</span>
        运行查询
      </button>
      <div class="user-menu-wrap">
        <button
          type="button"
          class="user-menu-btn"
          :title="userStore.user?.username ?? '用户菜单'"
          @click.stop="menuOpen = !menuOpen"
        >
          <User :size="16" :stroke-width="1.5" />
        </button>
        <div v-if="menuOpen" class="menu-pop">
          <span class="menu-user">{{ userStore.user?.username ?? '未登录' }}</span>
          <button type="button" @click="logout">退出</button>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.top-bar {
  display: grid;
  grid-template-columns: 180px minmax(360px, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 0 12px;
  background: var(--bg-raised);
  border-bottom: 1px solid var(--border-default);
  height: var(--workspace-topbar-height);
  min-height: var(--workspace-topbar-height);
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 1px;
  width: 180px;
  min-width: 0;
}

.brand-title {
  font-weight: 600;
  font-size: 15px;
  line-height: 1.2;
  color: var(--text-primary);
}

.brand-sub {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.top-center {
  display: flex;
  gap: 10px;
  min-width: 0;
  max-width: 1080px;
}

.dataset-select,
.search-input {
  height: var(--workspace-control-height);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  padding: 0 10px;
  font-size: 13px;
  color: var(--text-primary);
  min-width: 0;
}

.dataset-select {
  width: 240px;
  flex-shrink: 0;
}

.search-wrap {
  flex: 1;
  max-width: 760px;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  padding: 0 10px;
  height: var(--workspace-control-height);
}

.search-icon {
  color: var(--text-muted);
  font-size: 13px;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0;
  height: auto;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.btn-outline,
.btn-primary,
.user-menu-btn {
  height: var(--workspace-control-height);
  border-radius: var(--radius-control);
  font-size: 13px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}

.btn-outline {
  min-width: 92px;
  padding: 0 14px;
  border: 1px solid var(--border-default);
  background: var(--bg-panel);
  color: var(--text-primary);
}

.btn-primary {
  min-width: 106px;
  padding: 0 14px;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
  font-weight: 500;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.play-icon {
  font-size: 11px;
}

.user-menu-wrap {
  position: relative;
}

.user-menu-btn {
  width: 32px;
  padding: 0;
  border: 1px solid var(--border-default);
  background: var(--bg-panel);
  color: var(--text-primary);
}

.menu-pop {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 140px;
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  padding: 4px;
  z-index: 30;
  box-shadow: none;
}

.menu-user {
  display: block;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--text-secondary);
}

.menu-pop button {
  width: 100%;
  text-align: left;
  padding: 6px 10px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
}

.menu-pop button:hover {
  background: var(--bg-muted);
}
</style>
