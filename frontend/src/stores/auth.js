import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { refreshAccessToken } from '@/api/http'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('pm_user') || 'null'))
  const access = ref(localStorage.getItem('pm_access') || '')
  const refresh = ref(localStorage.getItem('pm_refresh') || '')

  const isLogin = computed(() => !!access.value)

  function persist() {
    localStorage.setItem('pm_user', JSON.stringify(user.value))
    localStorage.setItem('pm_access', access.value || '')
    localStorage.setItem('pm_refresh', refresh.value || '')
  }

  function setTokens(accessToken, refreshToken) {
    access.value = accessToken || ''
    if (refreshToken) refresh.value = refreshToken
    persist()
  }

  function applySession(data) {
    user.value = data.user
    setTokens(data.tokens.access, data.tokens.refresh)
    return data
  }

  async function login(email, password) {
    const data = await api.post('/auth/login/', { email, password })
    return applySession(data)
  }

  async function register(payload) {
    const data = await api.post('/auth/register/', payload)
    return applySession(data)
  }

  function logout() {
    user.value = null
    access.value = ''
    refresh.value = ''
    persist()
  }

  async function refreshTokens() {
    return refreshAccessToken()
  }

  async function fetchMe() {
    if (!access.value) return
    user.value = await api.get('/auth/me/')
    persist()
  }

  async function updateMe(payload) {
    user.value = await api.patch('/auth/me/', payload)
    persist()
  }

  return {
    user, access, refresh, isLogin,
    setTokens, login, register, logout, refreshTokens, fetchMe, updateMe,
  }
})
