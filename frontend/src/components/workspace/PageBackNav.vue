<script setup lang="ts">
import { useRouter } from 'vue-router'

const props = withDefaults(
  defineProps<{
    /** 返回目标；优先于 datasetId */
    to?: string
    /** 有数据集时回到工作区 */
    datasetId?: string
    /** 无历史记录时的默认路径 */
    fallback?: string
    label?: string
  }>(),
  {
    fallback: '/workspace',
    label: '返回工作区',
  },
)

const router = useRouter()

function goBack() {
  if (props.to) {
    void router.push(props.to)
    return
  }
  if (props.datasetId) {
    void router.push(`/workspace/${props.datasetId}`)
    return
  }
  if (window.history.length > 1) {
    router.back()
    return
  }
  void router.push(props.fallback)
}
</script>

<template>
  <nav class="page-back-nav" aria-label="页面导航">
    <button type="button" class="back-btn" @click="goBack">
      <span class="back-icon" aria-hidden="true">←</span>
      {{ label }}
    </button>
  </nav>
</template>

<style scoped>
.page-back-nav {
  margin-bottom: 12px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  background: var(--bg-panel);
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.back-btn:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.back-icon {
  font-size: 14px;
  line-height: 1;
}
</style>
