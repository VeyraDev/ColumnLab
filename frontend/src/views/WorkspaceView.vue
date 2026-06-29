<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import WorkspaceLayout from '@/layouts/WorkspaceLayout.vue'

const route = useRoute()
const datasetId = computed(() => route.params.datasetId as string | undefined)
</script>

<template>
  <WorkspaceLayout :dataset-id="datasetId" />
</template>
