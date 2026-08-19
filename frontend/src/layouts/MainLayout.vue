<template>
  <div class="layout">
    <header class="topbar">
      <router-link class="logo" to="/">
        <span class="mark">研</span>
        <span>PaperMind</span>
      </router-link>
      <nav class="nav">
        <router-link to="/">发现</router-link>
        <router-link to="/library">文献库</router-link>
        <router-link to="/graph">图谱</router-link>
        <router-link to="/vault">知识库</router-link>
        <router-link to="/community">社区交流</router-link>
        <router-link v-if="auth.user?.is_admin" to="/admin">管理</router-link>
      </nav>
      <div class="right">
        <el-popover
          placement="bottom-end"
          :width="380"
          trigger="click"
          @show="onOpenNotices"
        >
          <template #reference>
            <el-badge :value="notify.badge" :hidden="!notify.badge" :max="99" class="bell-wrap">
              <button type="button" class="bell-btn" title="消息通知">
                <el-icon :size="18"><Bell /></el-icon>
              </button>
            </el-badge>
          </template>
          <div class="notice-panel">
            <div class="notice-head">
              <b>消息通知</b>
              <el-button text size="small" :disabled="!notify.unread" @click="notify.markAllRead()">全部已读</el-button>
            </div>
            <div v-if="notify.inflight.length" class="notice-group">
              <div v-for="j in notify.inflight" :key="'j'+j.jobId" class="notice-item running">
                <div class="notice-title">正在导入</div>
                <div class="notice-body">《{{ j.title }}》后台解析中…</div>
              </div>
            </div>
            <div v-if="!notify.items.length && !notify.inflight.length" class="notice-empty">暂无消息</div>
            <div
              v-for="n in notify.items"
              :key="n.id"
              class="notice-item"
              :class="{unread: !n.is_read, [n.level]: true}"
              @click="openNotice(n)"
            >
              <div class="notice-title">{{ n.title }}</div>
              <div class="notice-body">{{ n.body }}</div>
              <div class="notice-time">{{ formatTime(n.created_at) }}</div>
            </div>
          </div>
        </el-popover>
        <el-dropdown trigger="click">
          <div class="avatar">{{ avatarText }}</div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/profile')">个人中心</el-dropdown-item>
              <el-dropdown-item v-if="auth.user?.is_admin" @click="$router.push('/admin')">用户与会员</el-dropdown-item>
              <el-dropdown-item divided @click="onLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useNotifyStore } from '@/stores/notify'

const auth = useAuthStore()
const notify = useNotifyStore()
const router = useRouter()
const avatarText = computed(() => auth.user?.avatar || auth.user?.username?.[0] || 'U')

onMounted(() => notify.startPolling())
onUnmounted(() => notify.stopPolling())

function onOpenNotices() {
  notify.fetchList()
}

function formatTime(iso) {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  if (!Number.isFinite(t)) return ''
  const diff = Date.now() - t
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前`
  return new Date(t).toLocaleString()
}

async function openNotice(n) {
  await notify.markRead(n.id)
  if (n.kind === 'membership') {
    const otherPaid = n.extra?.user_id && n.extra.user_id !== auth.user?.id
    if (auth.user?.is_admin && otherPaid) {
      router.push({ path: '/admin', query: { tab: 'orders' } })
    } else {
      router.push('/profile')
    }
    return
  }
  if (n.paper_id) {
    router.push({ name: 'library', query: { tab: 'reader', p: n.paper_id } })
  }
}

function onLogout() {
  notify.stopPolling()
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.topbar {
  position: sticky; top: 0; z-index: 50; height: var(--topbar-h);
  flex: none;
  background: rgba(255,255,255,.92); backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 20px; padding: 0 24px;
}
.logo {
  display: flex; align-items: center; gap: 8px;
  font-weight: 700; font-size: 17px; color: var(--text); text-decoration: none;
}
.mark {
  width: 30px; height: 30px; border-radius: 8px;
  background: linear-gradient(135deg, var(--primary), var(--purple));
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 800;
}
.nav { display: flex; gap: 2px; }
.nav a {
  padding: 7px 11px; border-radius: 8px; color: var(--text-2);
  font-weight: 500; text-decoration: none;
}
.nav a:hover, .nav a.router-link-exact-active {
  color: var(--primary); background: var(--primary-light);
}
.right { margin-left: auto; display: flex; align-items: center; gap: 14px; }
.bell-wrap { line-height: 1; }
.bell-btn {
  width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--border);
  background: #fff; color: var(--text-2); display: flex; align-items: center;
  justify-content: center; cursor: pointer;
}
.bell-btn:hover { color: var(--primary); border-color: var(--primary); background: var(--primary-light); }
.avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, #60a5fa, #8b5cf6);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-weight: 700; cursor: pointer;
}
main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
main > * {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: auto;
  scrollbar-gutter: stable;
}
.notice-panel { max-height: 420px; overflow: auto; margin: -8px; }
.notice-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 10px 8px; border-bottom: 1px solid var(--border);
  position: sticky; top: 0; background: #fff; z-index: 1;
}
.notice-empty { padding: 28px 12px; text-align: center; color: var(--text-3); }
.notice-item {
  padding: 10px 12px; border-bottom: 1px solid var(--border); cursor: pointer;
}
.notice-item:hover { background: var(--primary-light); }
.notice-item.unread { background: #f8fbff; }
.notice-item.running { cursor: default; background: #fffbeb; }
.notice-title { font-weight: 650; font-size: 13px; }
.notice-body { color: var(--text-2); font-size: 12.5px; margin-top: 2px; line-height: 1.45; }
.notice-time { color: var(--text-3); font-size: 11px; margin-top: 4px; }
.notice-item.error .notice-title { color: var(--danger); }
.notice-item.success .notice-title { color: #059669; }
</style>
