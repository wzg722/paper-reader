<template>
  <div class="community">
    <div class="subnav">
      <button type="button" class="pill" :class="{on: tab==='feed'}" @click="tab='feed'">✦ 动态</button>
      <button type="button" class="pill" :class="{on: tab==='teams'}" @click="tab='teams'">
        团队 <span class="count">({{ teamCount }})</span>
      </button>
      <button type="button" class="pill" :class="{on: tab==='shares'}" @click="tab='shares'">
        分享 <span class="count">({{ shareCount }})</span>
      </button>
    </div>

    <div v-show="tab==='feed'" class="feed-wrap">
      <article v-for="item in feed" :key="item.id" class="post">
        <header class="post-head">
          <div class="who">
            <span class="av">{{ displayAvatar(item.avatar, item.username) }}</span>
            <div>
              <div class="name">{{ item.username }}</div>
              <div class="sub">{{ item.role || '用户' }} · {{ relativeTime(item.created_at) }}</div>
            </div>
          </div>
          <span class="kind">{{ postKind(item) }}</span>
        </header>

        <button v-if="item.paper_title" type="button" class="paper-pill" @click="openPaper(item)">
          {{ item.paper_title }}
        </button>

        <p v-if="postBody(item)" class="body">{{ postBody(item) }}</p>

        <div v-if="postInsight(item)" class="insight">
          <span class="spark">✦</span>
          <span>{{ postInsight(item) }}</span>
        </div>

        <footer class="post-foot">
          <button type="button" class="act" :class="{on: item.liked}" @click="like(item)">♡ {{ item.like_count || 0 }}</button>
          <button type="button" class="act" @click="toggleComments(item)">💬 {{ item.comment_count || item._comments?.length || 0 }}</button>
          <span class="src-tag">论文社区</span>
        </footer>

        <div v-if="item._showComments" class="comments">
          <div v-for="c in item._comments || []" :key="c.id" class="c-item">
            <b>{{ c.username }}</b>
            <span>{{ c.content }}</span>
          </div>
          <el-input v-model="item._draft" size="small" placeholder="写评论…" @keyup.enter="sendComment(item)">
            <template #append><el-button @click="sendComment(item)">发送</el-button></template>
          </el-input>
        </div>
      </article>

      <div v-if="!feed.length" class="empty">还没有公开动态，去阅读器写一条公开笔记吧</div>

      <el-pagination
        class="pager"
        layout="total, slot, prev, pager, next, sizes"
        :total="feedTotal"
        v-model:current-page="feedPage"
        v-model:page-size="feedSize"
        :page-sizes="[5,10,20]"
        :hide-on-single-page="false"
        @current-change="loadFeed"
        @size-change="onFeedSize"
      >
        <template #default>
          <span class="page-info">{{ feedPage }}/{{ feedPageCount }}</span>
        </template>
      </el-pagination>
    </div>

    <div v-show="tab==='teams'" class="pane">
      <div class="toolbar">
        <span class="muted">已加入 {{ myTeams.length }} 个团队</span>
        <el-button type="primary" @click="createVisible=true">创建团队</el-button>
      </div>
      <article v-for="t in teamsPage" :key="t.id" class="post team-card">
        <header class="post-head">
          <div class="who">
            <span class="av">{{ displayAvatar(t.avatar, t.name) }}</span>
            <div>
              <div class="name">{{ t.name }}</div>
              <div class="sub">创建者 {{ t.owner_name }} · 成员 {{ t.member_count }}</div>
            </div>
          </div>
          <el-tag v-if="t.joined" size="small" type="success">已加入</el-tag>
        </header>
        <p class="body">{{ t.description || '暂无简介' }}</p>
        <footer class="post-foot">
          <el-button v-if="!t.joined" size="small" @click="applyTeam(t)">申请加入</el-button>
          <el-button v-if="t.is_owner" size="small" type="primary" @click="openManage(t)">管理</el-button>
          <span class="src-tag">团队</span>
        </footer>
      </article>
      <div v-if="!teams.length" class="empty">还没有团队，先创建一个</div>
      <el-pagination
        class="pager"
        layout="total, prev, pager, next, sizes"
        :total="teams.length"
        v-model:current-page="teamPage"
        v-model:page-size="teamSize"
        :page-sizes="[4,8,12]"
      />
    </div>

    <div v-show="tab==='shares'" class="pane">
      <el-radio-group v-model="shareDir" @change="onShareDir">
        <el-radio-button value="inbox">分享给我的</el-radio-button>
        <el-radio-button value="outbox">我分享的</el-radio-button>
      </el-radio-group>
      <article v-for="s in sharesPage" :key="s.id" class="post">
        <header class="post-head">
          <div class="who">
            <span class="av">{{ displayAvatar(s.from_avatar, s.from_user) }}</span>
            <div>
              <div class="name">{{ shareDir==='inbox' ? s.from_user : (s.target_username || ('团队 #' + s.target_team_id)) }}</div>
              <div class="sub">{{ s.from_role || '' }} · {{ relativeTime(s.created_at) }}</div>
            </div>
          </div>
          <span class="kind">分享</span>
        </header>
        <button v-if="s.paper_title" type="button" class="paper-pill" @click="openPaper(s)">{{ s.paper_title }}</button>
        <p v-if="s.message" class="body">{{ s.message }}</p>
        <footer class="post-foot">
          <template v-if="shareDir==='inbox'">
            <el-button size="small" type="primary" @click="shareAction(s, 'accept')">收下</el-button>
            <el-button size="small" @click="shareAction(s, 'ignore')">忽略</el-button>
          </template>
          <el-button v-else size="small" type="danger" @click="shareAction(s, 'revoke')">撤销</el-button>
          <span class="src-tag">论文社区</span>
        </footer>
      </article>
      <div v-if="!shares.length" class="empty">暂无分享记录</div>
      <el-pagination
        class="pager"
        layout="total, prev, pager, next, sizes"
        :total="shares.length"
        v-model:current-page="sharePage"
        v-model:page-size="shareSize"
        :page-sizes="[5,10,20]"
      />
    </div>

    <el-dialog v-model="createVisible" title="创建团队" width="420px">
      <el-input v-model="newTeam.name" placeholder="团队名称" />
      <el-input v-model="newTeam.description" type="textarea" placeholder="简介" style="margin-top:10px" />
      <template #footer>
        <el-button @click="createVisible=false">取消</el-button>
        <el-button type="primary" @click="createTeam">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="manageVisible" title="团队管理" width="520px">
      <h4>成员</h4>
      <div v-for="m in manageTeam?.members || []" :key="m.id" class="mrow">
        {{ m.user_info?.avatar }} {{ m.user_info?.username }} ({{ m.role }})
        <el-button v-if="m.role!=='owner'" size="small" type="danger" @click="removeMember(m)">移除</el-button>
      </div>
      <h4 style="margin-top:12px">待审批申请</h4>
      <div v-for="a in apps" :key="a.id" class="mrow">
        {{ a.avatar }} {{ a.username }}
        <el-button size="small" type="primary" @click="review(a, 'approve')">通过</el-button>
        <el-button size="small" @click="review(a, 'reject')">拒绝</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api/http'

const router = useRouter()
const tab = ref('feed')
const feed = ref([])
const feedPage = ref(1)
const feedSize = ref(5)
const feedTotal = ref(0)
const teams = ref([])
const myTeams = ref([])
const teamPage = ref(1)
const teamSize = ref(4)
const createVisible = ref(false)
const newTeam = reactive({ name: '', description: '' })
const manageVisible = ref(false)
const manageTeam = ref(null)
const apps = ref([])
const shares = ref([])
const inboxCount = ref(0)
const shareDir = ref('inbox')
const sharePage = ref(1)
const shareSize = ref(5)

const teamCount = computed(() => myTeams.value.length || teams.value.filter((t) => t.joined).length)
const shareCount = computed(() => inboxCount.value)
const teamsPage = computed(() => teams.value.slice((teamPage.value - 1) * teamSize.value, teamPage.value * teamSize.value))
const sharesPage = computed(() => shares.value.slice((sharePage.value - 1) * shareSize.value, sharePage.value * shareSize.value))
const feedPageCount = computed(() => Math.max(1, Math.ceil(feedTotal.value / feedSize.value)))

function displayAvatar(avatar, name) {
  const a = (avatar || '').trim()
  if (a && !/^https?:\/\//i.test(a) && !a.startsWith('/')) return a
  return (name || 'U')[0]
}

function postKind(item) {
  const note = (item.note_text || '').trim()
  const sum = (item.ai_summary || '').trim()
  if (sum && !note) return '论文总结'
  return '笔记'
}

function postBody(item) {
  return (item.note_text || '').trim() || (item.ai_summary || '').trim()
}

function postInsight(item) {
  const note = (item.note_text || '').trim()
  const sum = (item.ai_summary || '').trim()
  if (note && sum && sum !== note) return sum
  const sel = (item.sel_text || '').trim()
  if (sel && sel !== note) return sel
  return ''
}

function relativeTime(iso) {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  if (!Number.isFinite(t)) return ''
  const diff = Math.max(0, Date.now() - t)
  const m = Math.floor(diff / 60000)
  if (m < 1) return '刚刚'
  if (m < 60) return `${m}分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}小时前`
  const d = Math.floor(h / 24)
  return `${d}天前`
}

function openPaper(item) {
  const id = item.paper
  if (!id) return
  router.push({ name: 'library', query: { tab: 'reader', p: id } })
}

async function loadFeed() {
  const data = await api.get('/community/feed/', {
    params: { type: 'all', page: feedPage.value, page_size: feedSize.value },
  })
  feed.value = (data.results || []).map((x) => ({ ...x, _showComments: false, _comments: [], _draft: '' }))
  feedTotal.value = data.count || 0
}

function onFeedSize() {
  feedPage.value = 1
  loadFeed()
}

async function like(item) {
  const data = await api.post('/community/like/', { note_id: item.id })
  item.liked = data.liked
  item.like_count = data.like_count
}

async function toggleComments(item) {
  item._showComments = !item._showComments
  if (item._showComments) {
    const rows = await api.get('/community/comments/', { params: { note_id: item.id } })
    item._comments = Array.isArray(rows) ? rows : (rows.results || [])
    item.comment_count = item._comments.length
  }
}

async function sendComment(item) {
  if (!item._draft?.trim()) return
  await api.post('/community/comments/', { note_id: item.id, content: item._draft })
  item._draft = ''
  const rows = await api.get('/community/comments/', { params: { note_id: item.id } })
  item._comments = Array.isArray(rows) ? rows : (rows.results || [])
  item.comment_count = item._comments.length
}

async function loadTeams() {
  const data = await api.get('/teams/', { params: { page_size: 50 } })
  teams.value = data.results || data || []
  myTeams.value = await api.get('/teams/mine/') || []
}

async function createTeam() {
  if (!newTeam.name.trim()) return ElMessage.warning('请填写团队名称')
  await api.post('/teams/', newTeam)
  ElMessage.success('团队已创建')
  createVisible.value = false
  newTeam.name = ''
  newTeam.description = ''
  loadTeams()
}

async function applyTeam(t) {
  await api.post(`/teams/${t.id}/apply/`)
  ElMessage.success('申请已提交')
}

async function openManage(t) {
  manageTeam.value = await api.get(`/teams/${t.id}/`)
  apps.value = await api.get(`/teams/${t.id}/applications/`)
  manageVisible.value = true
}

async function review(a, action) {
  await api.post(`/teams/${manageTeam.value.id}/review/`, { application_id: a.id, action })
  apps.value = await api.get(`/teams/${manageTeam.value.id}/applications/`)
  manageTeam.value = await api.get(`/teams/${manageTeam.value.id}/`)
  loadTeams()
}

async function removeMember(m) {
  await api.post(`/teams/${manageTeam.value.id}/remove_member/`, { user_id: m.user })
  manageTeam.value = await api.get(`/teams/${manageTeam.value.id}/`)
}

async function loadShares() {
  const rows = await api.get('/papers/shares/', { params: { direction: shareDir.value } })
  shares.value = Array.isArray(rows) ? rows : (rows.results || [])
  sharePage.value = 1
  if (shareDir.value === 'inbox') inboxCount.value = shares.value.length
}

function onShareDir() {
  loadShares()
}

async function shareAction(s, action) {
  await api.post('/papers/shares/', { id: s.id, action })
  ElMessage.success('操作成功')
  loadShares()
}

watch(tab, (v) => {
  if (v === 'teams') loadTeams()
  if (v === 'shares') loadShares()
})

onMounted(async () => {
  await loadFeed()
  try { await loadTeams() } catch { /* ignore */ }
  try { await loadShares() } catch { /* ignore */ }
})
</script>

<style scoped>
.community {
  width: 100%;
  max-width: none;
  box-sizing: border-box;
  padding: 12px 20px 28px;
  min-height: 100%;
}
.subnav {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.pill {
  border: 0;
  background: transparent;
  color: var(--text-2);
  padding: 7px 16px;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
}
.pill.on {
  background: #eef2ff;
  color: #4f46e5;
}
.pill .count { font-weight: 500; color: inherit; }
.post {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 16px 18px 12px;
  margin-bottom: 12px;
}
.post-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.who { display: flex; gap: 10px; align-items: center; min-width: 0; }
.av {
  width: 40px; height: 40px; border-radius: 50%; flex: none;
  background: #eef2ff;
  color: #4f46e5; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 18px;
}
.name { font-weight: 700; font-size: 15px; }
.sub { color: var(--text-3); font-size: 12.5px; margin-top: 2px; }
.kind {
  color: #7c3aed;
  font-size: 13px;
  flex: none;
}
.paper-pill {
  display: block;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  text-align: left;
  margin-top: 12px;
  border: 0;
  background: #eef4ff;
  color: var(--text);
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
.paper-pill:hover { background: #e0eaff; color: var(--primary); }
.body {
  margin: 12px 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.insight {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-top: 10px;
  color: #2563eb;
  font-size: 13.5px;
  line-height: 1.55;
}
.spark { color: #f59e0b; flex: none; }
.post-foot {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
  padding-top: 8px;
}
.act {
  border: 0;
  background: none;
  color: var(--text-2);
  cursor: pointer;
  font-size: 14px;
  padding: 0;
}
.act.on { color: #ef4444; }
.act:hover { color: var(--primary); }
.src-tag {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-3);
  background: #f3f4f6;
  border-radius: 999px;
  padding: 3px 10px;
}
.comments {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.c-item { font-size: 13px; margin-bottom: 6px; display: flex; gap: 8px; }
.pager { margin-top: 8px; justify-content: center; width: 100%; }
.page-info { color: var(--text-3); font-size: 13px; margin: 0 8px; }
.empty { text-align: center; color: var(--text-3); padding: 40px 0; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.pane { padding-bottom: 8px; }
.pane :deep(.el-radio-group) { margin-bottom: 12px; }
.mrow { display: flex; gap: 8px; align-items: center; padding: 6px 0; }
</style>
