<template>
  <div class="vault">
    <div class="page-head">
      <h2>📚 个人论文知识库</h2>
      <span class="sub">已读论文的知识沉淀：AI 卡片 · 术语 · 笔记 · 一键导出 Obsidian</span>
    </div>

    <div class="stat-grid">
      <button
        v-for="s in statCards"
        :key="s.key"
        type="button"
        class="stat-mini"
        :title="s.tip"
        @click="onStat(s)"
      >
        <div class="n" :style="{ color: s.color }">{{ statValue(s) }}</div>
        <div class="l">{{ s.label }}</div>
      </button>
    </div>

    <div id="sec-cards" class="section-title">📚 已读论文 · AI 知识卡片</div>
    <div class="card-grid">
      <article
        v-for="c in cardsPage"
        :key="c.id"
        class="kb-card"
        @click="openPaper(c.id)"
      >
        <div class="t">{{ c.title }}</div>
        <div v-if="cardIntro(c)" class="intro">{{ cardIntro(c) }}</div>
        <div v-if="sumText(c, 'core')" class="hl star">⭐ {{ sumText(c, 'core') }}</div>
        <div v-if="sumText(c, 'insight') || sumText(c, 'method')" class="hl bulb">
          💡 {{ sumText(c, 'insight') || sumText(c, 'method') }}
        </div>
        <div class="ft">
          <span class="badge" :class="statusClass(c.status)">{{ c.status || '在读' }}</span>
          <span v-if="c.category" class="badge badge-purple">{{ c.category }}</span>
          <span>已读 {{ c.read_progress || 0 }}%</span>
          <span>📝 {{ c.note_count || 0 }}</span>
          <span class="year">{{ c.year || '—' }}</span>
        </div>
      </article>
      <div v-if="!cards.length" class="empty">
        <div class="big">📭</div>
        还没有精读完成的论文，去文献库开始吧
      </div>
    </div>
    <el-pagination
      v-if="cards.length"
      class="pager"
      layout="total, slot, prev, pager, next, sizes"
      :total="cards.length"
      v-model:current-page="cardPage"
      v-model:page-size="cardSize"
      :page-sizes="[5, 6, 10, 20]"
      :hide-on-single-page="false"
      @size-change="cardPage = 1"
    >
      <template #default>
        <span class="page-info">{{ cardPage }}/{{ cardPageCount }}</span>
      </template>
    </el-pagination>

    <div id="sec-terms" class="section-title">📖 术语库（跨论文沉淀）</div>
    <div class="term-panel card">
      <div class="term-head">
        <span class="en">英文术语</span>
        <span class="zh">中文译名</span>
        <span class="from">来源论文 / 说明</span>
      </div>
      <div
        v-for="t in termsPage"
        :key="t.id"
        class="term-row"
        :class="{ link: t.source_paper }"
        @click="t.source_paper && openPaper(t.source_paper)"
      >
        <span class="en">{{ t.term_en }}</span>
        <span class="zh">{{ t.term_zh }}</span>
        <span class="from">{{ termFrom(t) }}</span>
      </div>
      <div v-if="!terms.length" class="empty soft">暂无术语，精读时划词翻译会自动沉淀</div>
      <el-pagination
        v-if="terms.length"
        class="pager inner"
        layout="total, slot, prev, pager, next, sizes"
        :total="terms.length"
        v-model:current-page="termPage"
        v-model:page-size="termSize"
        :page-sizes="[5, 10, 20, 50]"
        :hide-on-single-page="false"
        @size-change="termPage = 1"
      >
        <template #default>
          <span class="page-info">{{ termPage }}/{{ termPageCount }}</span>
        </template>
      </el-pagination>
    </div>

    <div id="sec-notes" class="section-title">💬 我的笔记（按论文聚合）</div>
    <article v-for="g in noteGroupsPage" :key="g.paper" class="note-group card">
      <header class="note-head">
        <div class="title" @click="openPaper(g.paper)">📄 {{ g.title }}</div>
        <span class="muted">{{ g.notes.length }} 条笔记</span>
        <el-button type="primary" size="small" @click="readNote(g)">📖 阅读</el-button>
      </header>
      <div v-for="n in g.notes" :key="n.id" class="note-line">
        <i class="chip" :class="n.color || 'y'" />
        <span>{{ n.note_text || n.ai_summary || n.sel_text || '（空笔记）' }}</span>
      </div>
    </article>
    <div v-if="!noteGroups.length" class="empty soft">暂无笔记</div>
    <el-pagination
      v-if="noteGroups.length"
      class="pager"
      layout="total, slot, prev, pager, next, sizes"
      :total="noteGroups.length"
      v-model:current-page="notePage"
      v-model:page-size="noteSize"
      :page-sizes="[5, 10, 20]"
      :hide-on-single-page="false"
      @size-change="notePage = 1"
    >
      <template #default>
        <span class="page-info">{{ notePage }}/{{ notePageCount }}</span>
      </template>
    </el-pagination>

    <div class="section-title">📤 导出到 Obsidian 知识库</div>
    <div class="exp-block card">
      <p class="exp-desc">
        <b>把已读论文逐篇导入 Obsidian</b>：每篇论文生成一个独立 Markdown 文件（YAML frontmatter + AI 精读总结 + 摘要 + 术语 + 笔记），
        下载后放入 vault（<code>02-Areas/论文精读/</code>）即可检索与双链关联。
      </p>
      <div class="exp-toolbar">
        <b>待导入论文（{{ exportIds.length }} 篇）</b>
        <div class="grow" />
        <el-button size="small" @click="expToggleAll(true)">全选</el-button>
        <el-button size="small" @click="expToggleAll(false)">全不选</el-button>
      </div>
      <div class="exp-list">
        <label v-for="c in cards" :key="c.id" class="exp-item">
          <el-checkbox :model-value="exportIds.includes(c.id)" @change="(v) => expToggle(c.id, v)" />
          <span class="exp-title">📄 {{ c.title }}</span>
          <span class="muted">已读 {{ c.read_progress || 0 }}% · 📝 {{ c.note_count || 0 }}</span>
        </label>
        <div v-if="!cards.length" class="empty soft">暂无已读论文，先去文献库阅读吧</div>
      </div>
      <el-button type="primary" :loading="exporting" @click="exportMd">⬇ 导出所选论文（每篇一个 .md）</el-button>
    </div>

    <div class="tips card">
      <div class="tips-title">💡 知识库使用小贴士</div>
      <div class="tips-body">
        ① 读完论文后回到本页，AI 知识卡片自动沉淀（摘要/核心/方法/结果/局限）；<br>
        ② 术语库跨论文去重积累，精读时划词翻译自动命中；<br>
        ③ 笔记聚合按论文分组，点「📖 阅读」可回到阅读器继续精读；<br>
        ④ 每周导出一次 Obsidian，frontmatter + 双链让知识库可检索、可图谱关联。
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api/http'

const router = useRouter()
const overview = ref({ stats: {}, cards: [] })
const terms = ref([])
const notes = ref([])
const cardPage = ref(1)
const cardSize = ref(6)
const termPage = ref(1)
const termSize = ref(10)
const notePage = ref(1)
const noteSize = ref(5)
const exportIds = ref([])
const exporting = ref(false)

const statCards = [
  { key: 'cards', label: '知识卡片（已读）', color: 'var(--primary)', tip: '查看已读论文 AI 知识卡片', target: 'sec-cards' },
  { key: 'terms', label: '术语积累', color: 'var(--purple)', tip: '查看跨论文术语库', target: 'sec-terms' },
  { key: 'notes', label: '笔记', color: 'var(--accent)', tip: '查看我的笔记聚合', target: 'sec-notes' },
  { key: 'highlights', label: '高亮', color: 'var(--warn)', tip: '查看高亮与笔记', target: 'sec-notes' },
  { key: 'avg_progress', label: '平均精读进度', color: 'var(--danger)', tip: '前往文献库查看阅读进度', go: 'library' },
]

const cards = computed(() => overview.value.cards || [])
const cardsPage = computed(() => {
  const s = (cardPage.value - 1) * cardSize.value
  return cards.value.slice(s, s + cardSize.value)
})
const cardPageCount = computed(() => Math.max(1, Math.ceil(cards.value.length / cardSize.value) || 1))

const termsPage = computed(() => {
  const s = (termPage.value - 1) * termSize.value
  return terms.value.slice(s, s + termSize.value)
})
const termPageCount = computed(() => Math.max(1, Math.ceil(terms.value.length / termSize.value) || 1))

const noteGroups = computed(() => {
  const map = {}
  for (const n of notes.value) {
    if (!map[n.paper]) map[n.paper] = { paper: n.paper, title: n.paper_title, notes: [] }
    map[n.paper].notes.push(n)
  }
  return Object.values(map)
})
const noteGroupsPage = computed(() => {
  const s = (notePage.value - 1) * noteSize.value
  return noteGroups.value.slice(s, s + noteSize.value)
})
const notePageCount = computed(() => Math.max(1, Math.ceil(noteGroups.value.length / noteSize.value) || 1))

function statValue(s) {
  const v = overview.value.stats?.[s.key]
  if (s.key === 'avg_progress') return `${v ?? 0}%`
  return v ?? 0
}

function sumText(card, key) {
  const sm = card?.ai_summary || {}
  const val = sm[key]
  if (val == null || val === '') return ''
  if (typeof val === 'string') return val
  if (Array.isArray(val)) return val.filter(Boolean).join('；')
  if (typeof val === 'object') return val.zh || val.en || ''
  return String(val)
}

function cardIntro(c) {
  return (c.intro || c.title_zh || '').trim()
}

function statusClass(status) {
  if (status === '读完') return 'badge-green'
  if (status === '想读') return 'badge-orange'
  return 'badge-blue'
}

function termFrom(t) {
  const parts = []
  if (t.description) parts.push(t.description)
  if (t.paper_title) parts.push(`出自：${t.paper_title}`)
  return parts.join(' · ') || '—'
}

function onStat(s) {
  if (s.go === 'library') {
    router.push({ name: 'library' })
    return
  }
  scrollTo(s.target)
}

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function openPaper(id) {
  if (!id) return
  router.push({ name: 'library', query: { tab: 'mine', p: id } })
}

function readNote(g) {
  router.push({ name: 'library', query: { tab: 'reader', p: g.paper, mark: 'first' } })
}

function expToggle(id, on) {
  if (on) {
    if (!exportIds.value.includes(id)) exportIds.value = [...exportIds.value, id]
  } else {
    exportIds.value = exportIds.value.filter((x) => x !== id)
  }
}

function expToggleAll(on) {
  exportIds.value = on ? cards.value.map((c) => c.id) : []
}

async function load() {
  overview.value = await api.get('/vault/overview/')
  const t = await api.get('/reader/glossary/', { params: { page_size: 200 } })
  terms.value = t.results || t || []
  const n = await api.get('/reader/notes/', { params: { page_size: 200 } })
  notes.value = n.results || n || []
  if (!exportIds.value.length) expToggleAll(true)
}

async function exportMd() {
  if (!exportIds.value.length) return ElMessage.warning('请先勾选要导出的论文')
  exporting.value = true
  try {
    const data = await api.post('/vault/export/obsidian/', { paper_ids: exportIds.value })
    const files = data.files || []
    files.forEach((f, idx) => {
      const blob = new Blob([f.content], { type: 'text/markdown' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = f.filename
      setTimeout(() => a.click(), idx * 180)
    })
    ElMessage.success(`开始导出 ${files.length} 篇论文（每篇一个 .md）`)
  } catch (e) {
    ElMessage.error(e.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

watch(cards, (list) => {
  if (!exportIds.value.length && list.length) expToggleAll(true)
})

onMounted(load)
</script>

<style scoped>
.vault {
  width: 100%;
  max-width: none;
  min-width: 0;
  box-sizing: border-box;
  padding: 8px 24px 28px;
}
.page-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
  margin: 4px 0 14px;
}
.page-head h2 { font-size: 18px; font-weight: 700; margin: 0; }
.page-head .sub { color: var(--text-3); font-size: 13px; }

.stat-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}
.stat-mini {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
  cursor: pointer;
  min-width: 0;
  font: inherit;
}
.stat-mini:hover { border-color: var(--border-2); box-shadow: var(--shadow); }
.stat-mini .n { font-size: 22px; font-weight: 800; line-height: 1.2; }
.stat-mini .l { font-size: 12px; color: var(--text-3); margin-top: 2px; }

.section-title { margin-top: 18px; }

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(320px, 100%), 1fr));
  gap: 16px;
}
.kb-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  box-shadow: var(--shadow);
  transition: .15s;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.kb-card:hover {
  border-color: var(--border-2);
  box-shadow: var(--shadow-lg);
  transform: translateY(-1px);
}
.kb-card .t {
  font-weight: 700;
  font-size: 14.5px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.kb-card .intro {
  font-size: 12.5px;
  color: var(--text-2);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.kb-card .hl {
  font-size: 13px;
  color: var(--text-2);
  border-radius: 8px;
  padding: 8px 10px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.kb-card .hl.star {
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
}
.kb-card .hl.bulb {
  background: #f8fafc;
  border-left: 3px solid var(--primary);
}
.kb-card .ft {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-3);
  margin-top: auto;
  flex-wrap: wrap;
}
.kb-card .year { margin-left: auto; }
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}
.badge-blue { background: var(--primary-light); color: var(--primary); }
.badge-green { background: #ecfdf5; color: #059669; }
.badge-orange { background: #fff7ed; color: #ea580c; }
.badge-purple { background: #f5f3ff; color: #7c3aed; }

.term-panel { padding: 8px 18px 12px; }
.term-head, .term-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  padding: 8px 4px;
}
.term-head {
  color: var(--text-3);
  font-size: 12px;
  border-bottom: 1px solid var(--border);
}
.term-row { border-bottom: 1px solid #f1f4f9; }
.term-row:last-of-type { border-bottom: none; }
.term-row.link { cursor: pointer; }
.term-row.link:hover { background: #f8fafc; }
.term-head .en, .term-row .en { width: 200px; flex: none; font-weight: 600; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.term-head .zh, .term-row .zh { width: 140px; flex: none; color: var(--primary); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.term-head .from, .term-row .from { flex: 1; min-width: 0; color: var(--text-3); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.note-group { padding: 14px 18px; margin-bottom: 12px; }
.note-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.note-head .title {
  flex: 1;
  min-width: 0;
  font-weight: 700;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.note-head .title:hover { color: var(--primary); }
.note-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13.5px;
  padding: 6px 0;
  border-bottom: 1px dashed #f1f4f9;
  color: var(--text);
  overflow-wrap: anywhere;
}
.note-line:last-child { border-bottom: none; }
.chip {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  margin-top: 5px;
  flex: none;
  display: inline-block;
}
.chip.y { background: #fde68a; }
.chip.g { background: #a7f3d0; }
.chip.b { background: #bfdbfe; }
.chip.p { background: #fbcfe8; }
.chip.o { background: #fed7aa; }

.exp-block { padding: 16px 18px; }
.exp-desc { font-size: 13.5px; color: var(--text-2); margin-bottom: 10px; line-height: 1.6; }
.exp-desc code { font-size: 12px; background: #f1f5f9; padding: 1px 6px; border-radius: 4px; }
.exp-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.grow { flex: 1; }
.exp-list {
  max-height: 180px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px;
  margin-bottom: 12px;
}
.exp-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-bottom: 1px solid #f1f4f9;
  cursor: pointer;
  font-size: 13px;
}
.exp-item:last-child { border-bottom: none; }
.exp-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tips {
  padding: 14px 18px;
  margin-top: 16px;
  background: linear-gradient(135deg, #f5f3ff, #eff6ff);
  border-color: #e0e7ff;
}
.tips-title { font-weight: 700; font-size: 13.5px; margin-bottom: 8px; }
.tips-body { font-size: 12.5px; color: var(--text-2); line-height: 2; }

.pager {
  margin: 12px 0 4px;
  justify-content: center;
  flex-wrap: wrap;
}
.pager.inner { margin-top: 10px; }
.page-info {
  margin: 0 8px;
  color: var(--text-2);
  font-size: 13px;
  min-width: 36px;
  text-align: center;
}
.empty {
  grid-column: 1 / -1;
  padding: 36px 12px;
  text-align: center;
  color: var(--text-3);
}
.empty.soft { padding: 18px 8px; }
.empty .big { font-size: 28px; margin-bottom: 6px; }

@media (max-width: 900px) {
  .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .term-head .en, .term-row .en { width: 120px; }
  .term-head .zh, .term-row .zh { width: 90px; }
}
@media (max-width: 640px) {
  .vault { padding: 8px 14px 24px; }
  .term-head, .term-row { flex-wrap: wrap; }
  .term-head .en, .term-row .en,
  .term-head .zh, .term-row .zh,
  .term-head .from, .term-row .from { width: 100%; white-space: normal; }
}
</style>
