import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import type { ApiResponse } from '@/types/api'
import { TOKEN_KEY, USER_KEY } from '@/types/api'

const request = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

request.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse
    if (body && typeof body.code === 'number' && body.code !== 0) {
      ElMessage.error(body.msg || '请求失败')
      return Promise.reject(new Error(body.msg))
    }
    return response
  },
  (error: AxiosError<ApiResponse>) => {
    const msg = error.response?.data?.msg || error.message || '网络错误'
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }
    ElMessage.error(msg)
    return Promise.reject(error)
  },
)

export default request
