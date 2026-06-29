import request from './request'
import { TOKEN_KEY } from '@/types/api'

export interface UploadResult {
  job_id: number
  dataset_id: number
  source_sha256: string
}

export interface ImportJobState {
  id: number
  dataset_id: number
  status: string
  stage: string
  bytes_processed: number
  rows_processed: number
  current_column: string
  error_count: number
  error_code?: string | null
  error_message?: string | null
  error_samples?: Array<{ row: number; column: string; value: string; reason: string }>
}

export async function uploadDataset(
  file: File,
  options: {
    tableName?: string
    importMode?: 'strict' | 'coerce'
    schemaOverrides?: string
    targetBlockBytes?: number
  } = {},
) {
  const form = new FormData()
  form.append('file', file)
  form.append('table_name', options.tableName ?? 'data')
  form.append('import_mode', options.importMode ?? 'strict')
  form.append('schema_overrides', options.schemaOverrides ?? '[]')
  form.append('target_block_bytes', String(options.targetBlockBytes ?? 65536))
  const { data } = await request.post<{ data: UploadResult }>('/datasets/uploads', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data.data
}

export async function getImportJob(jobId: number) {
  const { data } = await request.get<{ data: ImportJobState }>(`/import-jobs/${jobId}`)
  return data.data
}

export async function cancelImportJob(jobId: number) {
  const { data } = await request.post<{ data: ImportJobState }>(`/import-jobs/${jobId}/cancel`)
  return data.data
}

export function subscribeImportEvents(
  jobId: number,
  onEvent: (payload: Partial<ImportJobState> & { stage?: string; message?: string }) => void,
): () => void {
  const token = localStorage.getItem(TOKEN_KEY)
  const url = `/api/import-jobs/${jobId}/events`
  const source = new EventSource(url, { withCredentials: true })
  // EventSource cannot set Authorization header; rely on cookie-less dev proxy.
  // Fallback: poll via getImportJob when SSE fails.
  void token

  source.onmessage = (event) => {
    try {
      onEvent(JSON.parse(event.data))
    } catch {
      /* ignore malformed */
    }
  }

  source.onerror = () => {
    source.close()
  }

  return () => source.close()
}
