import { defineStore } from 'pinia'
import { ref } from 'vue'
import { deleteDataset, listDatasets, type DatasetSummary } from '@/api/datasets'

export const useDatasetStore = defineStore('dataset', () => {
  const datasets = ref<DatasetSummary[]>([])
  const loading = ref(false)
  const deletingId = ref<number | null>(null)

  async function fetchDatasets() {
    loading.value = true
    try {
      datasets.value = await listDatasets()
    } finally {
      loading.value = false
    }
  }

  async function removeDataset(id: number) {
    deletingId.value = id
    try {
      await deleteDataset(id)
      datasets.value = datasets.value.filter((ds) => ds.id !== id)
    } finally {
      deletingId.value = null
    }
  }

  return { datasets, loading, deletingId, fetchDatasets, removeDataset }
})
