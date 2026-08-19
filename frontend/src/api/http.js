import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

const raw = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

function isAuthFreeUrl(url = '') {
  return /\/auth\/(login|register|refresh)\/?(\?|$)/.test(url)
}

function unwrap(body) {
  if (body && typeof body === 'object' && 'code' in body) {
    if (body.code !== 0) {
      throw new Error(body.message || '请求失败')
    }
    return body.data
  }
  return body
}

let refreshTask = null

export async function refreshAccessToken() {
  const auth = useAuthStore()
  if (!auth.refresh) throw new Error('未登录')
  if (!refreshTask) {
    refreshTask = raw
      .post('/auth/refresh/', { refresh: auth.refresh })
      .then((res) => {
        const data = unwrap(res.data) || {}
        if (!data.access) throw new Error('登录已过期')
        auth.setTokens(data.access, data.refresh || auth.refresh)
        return data.access
      })
      .finally(() => {
        refreshTask = null
      })
  }
  return refreshTask
}

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.access && !isAuthFreeUrl(config.url || '')) {
    config.headers.Authorization = `Bearer ${auth.access}`
  }
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    if (config.headers) {
      delete config.headers['Content-Type']
    }
  }
  return config
})

api.interceptors.response.use(
  (res) => unwrap(res.data),
  async (err) => {
    const original = err.config || {}
    const status = err.response?.status
    if (status === 401 && !original._retry && !isAuthFreeUrl(original.url || '')) {
      original._retry = true
      try {
        const access = await refreshAccessToken()
        original.headers = original.headers || {}
        original.headers.Authorization = `Bearer ${access}`
        return api(original)
      } catch {
        const auth = useAuthStore()
        auth.logout()
        const current = router.currentRoute.value
        if (current.name !== 'login') {
          router.replace({ name: 'login', query: { redirect: current.fullPath } })
        }
      }
    }
    const msg = err.response?.data?.message || err.response?.data?.detail || err.message
    return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)))
  },
)

export default api
