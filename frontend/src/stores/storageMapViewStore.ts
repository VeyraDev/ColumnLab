import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useStorageMapViewStore = defineStore('storageMapView', () => {
  /** 0 = 自动填满可用宽度；否则为可见块数上限。 */
  const visibleBlockDensity = ref(0)
  const displayMode = ref<'row_range'>('row_range')

  return {
    visibleBlockDensity,
    displayMode,
  }
})
