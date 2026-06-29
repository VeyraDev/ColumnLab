<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import TopBar from '@/components/workspace/TopBar.vue'
import PageBackNav from '@/components/workspace/PageBackNav.vue'
import QueryPanel from '@/components/query-editor/QueryPanel.vue'

const route = useRoute()
const datasetId = computed(() => route.params.datasetId as string | undefined)
</script>

<template>
  <div class="query-view">
    <TopBar :dataset-id="datasetId" />
    <div class="query-toolbar">
      <PageBackNav :dataset-id="datasetId" label="返回工作区" />
    </div>
    <main class="query-main">
      <QueryPanel :dataset-id="datasetId" />
    </main>
  </div>
</template>

<style scoped>
.query-view {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  height: 100vh;
  background: var(--bg-app);
}

.query-toolbar {
  padding: 6px 12px;
  background: var(--bg-muted);
  border-bottom: 1px solid var(--border-default);
}

.query-toolbar :deep(.page-back-nav) {
  margin-bottom: 0;
}

.query-main {
  min-height: 0;
  overflow: hidden;
}
</style>
