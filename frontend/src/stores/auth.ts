import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi, type LoginResult } from '@/api/auth'

const TOKEN_KEY = 'ai_platform_token'
const USER_KEY = 'ai_platform_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<LoginResult['user'] | null>(
    JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  )

  async function login(username: string, password: string) {
    const res = await authApi.login(username, password)
    token.value = res.data.access_token
    user.value = res.data.user
    localStorage.setItem(TOKEN_KEY, res.data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(res.data.user))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const isLoggedIn = () => !!token.value

  return { token, user, login, logout, isLoggedIn }
})
