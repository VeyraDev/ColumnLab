export const TOKEN_KEY = 'columnlab_token'
export const USER_KEY = 'columnlab_user'

export interface ApiResponse<T = unknown> {
  code: number
  msg: string
  data: T
}

export interface AuthResult {
  access_token: string
  user_id: number
  username: string
}

export interface UserProfile {
  id: number
  username: string
  email: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
}
