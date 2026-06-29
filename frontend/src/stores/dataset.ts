import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listDatasets, type DatasetSummary } from '@/api/datasets'

export const useDatasetStore = defineStore('dataset', () => {
  const datasets = ref<DatasetSummary[]>([])
  const loading = ref(false)

  async function fetchDatasets() {
    loading.value = true
    try {
      datasets.value = await listDatasets()
    } finally {
      loading.value = false
    }
  }

  return { datasets, loading, fetchDatasets }
})
