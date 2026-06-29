import request from './request'
import type { ApiResponse, AuthResult, LoginPayload, RegisterPayload, UserProfile } from '@/types/api'

export function register(payload: RegisterPayload) {
  return request.post<ApiResponse<AuthResult>>('/auth/register', payload)
}

export function login(payload: LoginPayload) {
  return request.post<ApiResponse<AuthResult>>('/auth/login', payload)
}

export function getProfile() {
  return request.get<ApiResponse<UserProfile>>('/auth/profile')
}
