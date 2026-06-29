import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useStorageMapViewStore = defineStore('storageMapView', () => {
  const blocksPerRow = ref(6)
  const displayMode = ref<'row_range'>('row_range')

  return {
    blocksPerRow,
    displayMode,
  }
})
