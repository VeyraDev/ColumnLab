import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  cancelImportJob,
  getImportJob,
  uploadDataset,
  type ImportJobState,
} from '@/api/import'

export const useImportJobStore = defineStore('importJob', () => {
  const currentJob = ref<ImportJobState | null>(null)
  const uploading = ref(false)
  let pollTimer: number | null = null

  function stopPolling() {
    if (pollTimer !== null) {
      window.clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function pollJob(jobId: number) {
    currentJob.value = await getImportJob(jobId)
    if (['completed', 'failed', 'cancelled'].includes(currentJob.value.status)) {
      stopPolling()
    }
    return currentJob.value
  }

  function startPolling(jobId: number) {
    stopPolling()
    pollTimer = window.setInterval(() => {
      void pollJob(jobId)
    }, 500)
  }

  async function upload(
    file: File,
    options: {
      importMode?: 'strict' | 'coerce'
      tableName?: string
      targetBlockBytes?: number
    } = {},
  ) {
    uploading.value = true
    stopPolling()
    try {
      const result = await uploadDataset(file, options)
      await pollJob(result.job_id)
      startPolling(result.job_id)
      return result
    } finally {
      uploading.value = false
    }
  }

  async function cancel(jobId: number) {
    currentJob.value = await cancelImportJob(jobId)
    stopPolling()
  }

  return {
    currentJob,
    uploading,
    upload,
    pollJob,
    startPolling,
    stopPolling,
    cancel,
  }
})
