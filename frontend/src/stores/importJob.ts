import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  cancelImportJob,
  getImportJob,
  subscribeImportEvents,
  uploadDataset,
  type ImportJobState,
} from '@/api/import'

export const useImportJobStore = defineStore('importJob', () => {
  const currentJob = ref<ImportJobState | null>(null)
  const uploading = ref(false)
  let pollTimer: number | null = null
  let unsubscribeSse: (() => void) | null = null

  function stopPolling() {
    if (pollTimer !== null) {
      window.clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function stopSse() {
    if (unsubscribeSse) {
      unsubscribeSse()
      unsubscribeSse = null
    }
  }

  function stopTracking() {
    stopPolling()
    stopSse()
  }

  function applyJobUpdate(payload: Partial<ImportJobState>) {
    if (!currentJob.value) return
    currentJob.value = { ...currentJob.value, ...payload }
    if (['completed', 'failed', 'cancelled'].includes(currentJob.value.status)) {
      stopTracking()
    }
  }

  async function pollJob(jobId: number) {
    currentJob.value = await getImportJob(jobId)
    if (['completed', 'failed', 'cancelled'].includes(currentJob.value.status)) {
      stopTracking()
    }
    return currentJob.value
  }

  function startPolling(jobId: number) {
    stopPolling()
    pollTimer = window.setInterval(() => {
      void pollJob(jobId)
    }, 500)
  }

  function startSse(jobId: number) {
    stopSse()
    unsubscribeSse = subscribeImportEvents(jobId, (payload) => {
      applyJobUpdate(payload)
    })
    // SSE onerror closes the source; fall back to polling if task still active.
    window.setTimeout(() => {
      if (
        currentJob.value &&
        !['completed', 'failed', 'cancelled'].includes(currentJob.value.status) &&
        pollTimer === null
      ) {
        startPolling(jobId)
      }
    }, 2000)
  }

  function trackJob(jobId: number) {
    stopTracking()
    startSse(jobId)
  }

  async function upload(
    file: File,
    options: {
      importMode?: 'strict' | 'coerce'
      tableName?: string
      targetBlockBytes?: number
      schemaOverrides?: string
    } = {},
  ) {
    uploading.value = true
    stopTracking()
    try {
      const result = await uploadDataset(file, options)
      await pollJob(result.job_id)
      trackJob(result.job_id)
      return result
    } finally {
      uploading.value = false
    }
  }

  async function cancel(jobId: number) {
    currentJob.value = await cancelImportJob(jobId)
    stopTracking()
  }

  return {
    currentJob,
    uploading,
    upload,
    pollJob,
    startPolling,
    stopPolling,
    stopTracking,
    cancel,
  }
})
