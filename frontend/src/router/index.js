import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'discover', component: () => import('@/views/DiscoverView.vue') },
      { path: 'library', name: 'library', component: () => import('@/views/LibraryView.vue') },
      { path: 'reader/:id?', name: 'reader', component: () => import('@/views/ReaderView.vue') },
      { path: 'graph', name: 'graph', component: () => import('@/views/GraphView.vue') },
      { path: 'vault', name: 'vault', component: () => import('@/views/VaultView.vue') },
      { path: 'community', name: 'community', component: () => import('@/views/CommunityView.vue') },
      { path: 'profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
      { path: 'admin', name: 'admin', component: () => import('@/views/AdminView.vue'), meta: { admin: true } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function isPublicRoute(to) {
  return to.matched.some((record) => record.meta.public)
}

function safeRedirect(raw) {
  if (typeof raw !== 'string') return '/'
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/login') || raw.startsWith('/register')) {
    return '/'
  }
  return raw
}

let sessionChecked = false

router.beforeEach(async (to) => {
  document.title = 'PaperMind'
  const auth = useAuthStore()

  if (!sessionChecked) {
    sessionChecked = true
    if (auth.access) {
      try {
        await auth.fetchMe()
      } catch {
        try {
          await auth.refreshTokens()
          await auth.fetchMe()
        } catch {
          auth.logout()
        }
      }
    }
  }

  if (!auth.isLogin) {
    if (isPublicRoute(to)) return true
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (isPublicRoute(to)) return { path: safeRedirect(to.query.redirect) }
  if (to.meta.admin && !auth.user?.is_admin) return { name: 'discover' }
  return true
})

export default router
