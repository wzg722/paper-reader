import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ElNotification } from 'element-plus'
import api from '@/api/http'

export const useNotifyStore = defineStore('notify', () => {
  const items = ref([])
  const unread = ref(0)
  const inflight = ref([])
  const loading = ref(false)
  const lastSeenAt = ref(0)
  let timer = null
  let started = false

  const badge = computed(() => unread.value + inflight.value.length)

  function watchJob(jobId, title, paperId) {
    const id = Number(jobId)
    if (!id) return
    if (inflight.value.some((x) => x.jobId === id)) return
    inflight.value = [
      { jobId: id, title: title || '论文', paperId: paperId || null, startedAt: Date.now() },
      ...inflight.value,
    ]
  }

  async function fetchList({ toastNew = false } = {}) {
    loading.value = true
    try {
      const data = await api.get('/auth/notifications/', { params: { page: 1, page_size: 30 } })
      const rows = data.results || []
      if (toastNew && lastSeenAt.value) {
        const seen = lastSeenAt.value
        for (const n of [...rows].reverse()) {
          const ts = new Date(n.created_at).getTime()
          if (ts > seen && !n.is_read) {
            ElNotification({
              type: n.level === 'error' ? 'error' : (n.level === 'success' ? 'success' : 'info'),
              title: n.title,
              message: n.body,
              duration: 6000,
            })
          }
        }
      }
      items.value = rows
      unread.value = data.unread_count || 0
      lastSeenAt.value = Date.now()
    } catch {
      /* ignore while logged out / network blip */
    } finally {
      loading.value = false
    }
  }

  async function checkJobs() {
    const jobs = inflight.value.slice()
    if (!jobs.length) return
    const done = []
    for (const j of jobs) {
      try {
        const job = await api.get('/papers/import-jobs/', { params: { id: j.jobId } })
        if (job.status === 'success' || job.status === 'failed') done.push(j.jobId)
      } catch { /* keep */ }
    }
    if (done.length) {
      inflight.value = inflight.value.filter((x) => !done.includes(x.jobId))
      await fetchList({ toastNew: true })
    }
  }

  async function tick() {
    await checkJobs()
    await fetchList({ toastNew: true })
  }

  function startPolling() {
    if (started) return
    started = true
    lastSeenAt.value = Date.now()
    fetchList()
    timer = setInterval(tick, 8000)
  }

  function stopPolling() {
    started = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    items.value = []
    unread.value = 0
    inflight.value = []
  }

  async function markRead(id) {
    try {
      const row = await api.post(`/auth/notifications/${id}/read/`)
      items.value = items.value.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      unread.value = items.value.filter((n) => !n.is_read).length
      return row
    } catch {
      return null
    }
  }

  async function markAllRead() {
    try {
      await api.post('/auth/notifications/read-all/')
      items.value = items.value.map((n) => ({ ...n, is_read: true }))
      unread.value = 0
    } catch { /* ignore */ }
  }

  return {
    items, unread, inflight, loading, badge,
    watchJob, fetchList, startPolling, stopPolling, markRead, markAllRead,
  }
})
