import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getProfile, login as loginApi, register as registerApi, type AuthResult, type RegisterPayload, type LoginPayload } from '@/api/auth'
import { TOKEN_KEY, USER_KEY } from '@/types/api'

interface StoredUser {
  id: number
  username: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<StoredUser | null>(loadUser())

  const isLoggedIn = computed(() => !!token.value)

  function loadUser(): StoredUser | null {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as StoredUser
    } catch {
      return null
    }
  }

  function setSession(result: AuthResult) {
    token.value = result.access_token
    user.value = { id: result.user_id, username: result.username }
    localStorage.setItem(TOKEN_KEY, result.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  function clearSession() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  async function login(payload: LoginPayload) {
    const res = await loginApi(payload)
    setSession(res.data.data)
  }

  async function register(payload: RegisterPayload) {
    const res = await registerApi(payload)
    setSession(res.data.data)
  }

  async function fetchProfile() {
    const res = await getProfile()
    const profile = res.data.data
    user.value = { id: profile.id, username: profile.username }
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  function logout() {
    clearSession()
  }

  return {
    token,
    user,
    isLoggedIn,
    login,
    register,
    fetchProfile,
    logout,
    clearSession,
  }
})
