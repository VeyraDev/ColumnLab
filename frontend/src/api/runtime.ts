import request from './request'

export interface RuntimeInfo {
  engine_version: string
  memory_used_bytes: number
  memory_total_bytes: number
  process_rss_bytes: number
}

export async function fetchRuntime() {
  const { data } = await request.get<{ data: RuntimeInfo }>('/runtime')
  return data.data
}
