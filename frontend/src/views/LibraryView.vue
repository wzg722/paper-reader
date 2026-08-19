<template>
  <div class="lib">
    <el-tabs v-model="tab" class="tabs" @tab-change="onTabChange">
      <el-tab-pane label="📚 我的文献" name="mine" />
      <el-tab-pane label="⭐ 收藏网站" name="sources" />
      <el-tab-pane label="📖 阅读器" name="reader" />
      <el-tab-pane label="📥 导入文献" name="import" />
    </el-tabs>

    <!-- 我的文献 -->
    <div v-show="tab==='mine'" class="mine-layout">
      <aside class="side card">
        <div class="side-item" :class="{active: !filters.category && !filters.starred && !trash}" @click="setFolder()">
          📚 全部 <span class="cnt">{{ counts.all }}</span>
        </div>
        <div
          v-for="f in folderFlat"
          :key="f.id"
          class="side-item folder"
          :class="{active: filters.category===f.id}"
          :style="{ paddingLeft: (10 + f.depth * 14) + 'px' }"
          @click="setFolder(f.id)"
          @contextmenu.prevent="onFolderMenu(f)"
        >
          <button
            v-if="f.child_count"
            type="button"
            class="twist"
            @click.stop="toggleExpand(f.id)"
          >{{ isExpanded(f.id) ? '▾' : '▸' }}</button>
          <span v-else class="twist-sp"></span>
          <span class="fname">📁 {{ f.name }}</span>
          <span class="cnt">{{ f.paper_count }}</span>
        </div>
        <div class="side-item" :class="{active: filters.starred}" @click="setStarred()">⭐ 收藏</div>
        <div class="side-item" :class="{active: trash}" @click="setTrash()">🗑 回收站</div>
      </aside>

      <section class="list">
        <div class="crumb" v-if="!trash && !filters.starred">
          <button type="button" class="crumb-link" @click="setFolder()">全部</button>
          <template v-for="(c, i) in breadcrumb" :key="c.id">
            <span class="crumb-sep">/</span>
            <button type="button" class="crumb-link" :class="{current: i===breadcrumb.length-1}" @click="setFolder(c.id)">{{ c.name }}</button>
          </template>
        </div>
        <div class="toolbar">
          <el-button type="primary" size="small" :disabled="!!trash" @click="createFolder()">＋ 新建文件夹</el-button>
          <el-select v-model="filters.status" clearable placeholder="阅读状态" style="width:120px" @change="onPaperFilter">
            <el-option label="想读" value="想读" />
            <el-option label="在读" value="在读" />
            <el-option label="读完" value="读完" />
          </el-select>
          <el-input v-model="filters.search" placeholder="搜索" clearable style="width:220px" @keyup.enter="onPaperFilter" />
          <el-button @click="onPaperFilter">筛选</el-button>
          <span class="muted hint">右击论文改信息 · 右击文件夹可重命名/删除</span>
        </div>

        <div
          v-for="p in papers"
          :key="p.id"
          class="paper-card row"
          @click="select(p)"
          @contextmenu.prevent="openEdit(p)"
        >
          <div class="grow">
            <div class="title" :class="{trash: trash}">{{ p.title }}</div>
            <div class="intro-tag" v-if="p.intro">📌 {{ p.intro }}</div>
            <div class="muted">{{ p.authors }} · {{ p.year }}</div>
            <div class="meta">
              <span class="badge badge-blue">{{ p.status }}</span>
              <span class="badge" v-if="p.category_name">{{ p.category_name }}</span>
              <el-progress :percentage="p.read_progress || 0" :stroke-width="6" style="width:120px" />
            </div>
          </div>
          <div class="actions" @click.stop>
            <el-button size="small" type="primary" @click="read(p)">阅读</el-button>
            <el-button v-if="!trash" size="small" @click="remove(p)">🗑</el-button>
            <template v-else>
              <el-button size="small" @click="restore(p)">恢复</el-button>
              <el-button size="small" type="danger" @click="purge(p)">彻底删除</el-button>
            </template>
          </div>
        </div>
        <div v-if="!papers.length" class="muted" style="padding:40px;text-align:center">
          {{ emptyHint }}
        </div>

        <el-pagination
          class="pager"
          layout="total, prev, pager, next, sizes, jumper"
          :total="total"
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[5,10,20,50]"
          :hide-on-single-page="false"
          @current-change="loadPapers"
          @size-change="onPaperSize"
        />
      </section>

      <aside class="detail card">
        <template v-if="current">
          <h3>{{ current.title }}</h3>
          <p class="muted" v-if="current.title_zh">{{ current.title_zh }}</p>
          <p>{{ current.intro }}</p>
          <p class="muted">{{ current.authors }}</p>
          <div class="meta">
            <span class="badge badge-blue">{{ current.status }}</span>
            <el-button size="small" @click="toggleStar">{{ current.starred ? '★' : '☆' }}</el-button>
          </div>
          <el-button type="primary" style="width:100%;margin-top:12px" @click="read(current)">📖 阅读论文</el-button>
          <el-button
            v-if="!current.content_json?.length && (current.arxiv_id || current.cover_url)"
            style="width:100%;margin-top:8px"
            :loading="fetchingPdf"
            @click="fetchPdf(current)"
          >⬇ 下载 PDF 正文</el-button>
          <el-button style="width:100%;margin-top:8px" @click="openShare">📤 分享</el-button>
          <div v-if="summaryView" class="summary">
            <h4>AI 总结</h4>
            <div v-for="s in summaryView.sections" :key="s.key" class="sum-sec">
              <h5>{{ s.title }}</h5>
              <p v-if="s.zh" class="sum-zh">{{ s.zh }}</p>
              <p v-if="s.en" class="sum-en">{{ s.en }}</p>
            </div>
            <div v-if="summaryView.glossary.length" class="sum-sec">
              <h5>术语</h5>
              <p v-for="(g, i) in summaryView.glossary" :key="i" class="sum-term">
                <b>{{ g.en }}</b>
                <span v-if="g.zh"> {{ g.zh }}</span>
              </p>
            </div>
          </div>
          <p class="abs">{{ current.abstract }}</p>
        </template>
        <div v-else class="folder-pane">
          <div class="folder-hero">{{ currentFolder ? '📁 ' + currentFolder.name : '📚 我的文献' }}</div>
          <p class="muted">{{ currentFolder ? '当前文件夹，可继续新建子文件夹，或从中间列表点选论文' : '从中间列表点选论文查看详情' }}</p>
          <el-button type="primary" :disabled="!!trash" @click="createFolder()" style="width:100%;margin-top:12px">
            {{ currentFolder ? '＋ 在此新建子文件夹' : '＋ 新建文件夹' }}
          </el-button>
        </div>
      </aside>
    </div>

    <!-- 收藏网站 -->
    <div v-show="tab==='sources'" class="sources-wrap">
      <div class="section-tip muted">{{ sourceTip }}</div>
      <div class="sources">
        <div
          v-for="s in sources"
          :key="s.id"
          class="card src"
          :class="{active: activeSource?.id===s.id}"
          @click="selectSource(s)"
        >
          <b>{{ s.name }}</b>
          <div class="muted">{{ s.url }}</div>
          <el-tag size="small" type="success" style="margin-top:6px">可检索</el-tag>
        </div>
      </div>

      <div class="card" style="padding:16px;margin-top:12px">
        <el-input v-model="arxivQ" :placeholder="sourcePlaceholder" @keyup.enter="searchSource">
          <template #append>
            <el-button @click="searchSource" :loading="searching">搜索</el-button>
          </template>
        </el-input>
        <div class="sel-bar">
          <el-select v-model="searchSort" size="small" style="width:158px" @change="onSearchSort">
            <el-option v-for="o in searchSortOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <template v-if="arxivResults.length">
            <el-checkbox v-model="selAll" @change="toggleSelAll">全选本页</el-checkbox>
            <span class="muted">已选 {{ selectedIds.length }} 篇 · 共 {{ searchTotal }} 篇</span>
            <el-button type="primary" size="small" :disabled="!selectedIds.length" @click="importSelected">
              ＋ 导入所选
            </el-button>
          </template>
        </div>
        <div v-for="r in arxivResults" :key="hitKey(r)" class="arxiv-item">
          <el-checkbox
            :model-value="selectedIds.includes(hitKey(r))"
            :disabled="!!r.in_library"
            @change="(v)=>toggleSel(hitKey(r), v)"
          />
          <div class="grow">
            <b>{{ r.title }}</b>
            <div class="muted">{{ r.authors }} · {{ r.year || '—' }} · {{ r.venue || r.source || '' }} {{ r.arxiv_id || r.doi || '' }}<span v-if="r.cites"> · 被引 {{ r.cites }}</span></div>
            <div class="muted" style="font-size:12px;margin-top:2px">{{ (r.abstract || r.intro || '').slice(0, 120) }}{{ (r.abstract || r.intro || '').length > 120 ? '…' : '' }}</div>
          </div>
          <el-button v-if="r.abs_url || r.doi" size="small" @click="openHit(r)">原文</el-button>
          <el-button v-if="r.in_library" size="small" type="primary" @click="read({ id: r.paper_id })">阅读</el-button>
          <el-button v-else size="small" type="primary" :loading="importingId===hitKey(r)" @click="openHitImport([r])">导入</el-button>
        </div>
        <div v-if="searching && !arxivResults.length" class="muted" style="padding:24px;text-align:center">正在检索…</div>
        <div v-else-if="!arxivResults.length && searched" class="muted" style="padding:24px;text-align:center">无结果，换个关键词试试</div>
        <el-pagination
          v-if="searchTotal > 0"
          class="pager"
          layout="total, prev, pager, next, sizes, jumper"
          :total="searchTotal"
          v-model:current-page="searchPage"
          v-model:page-size="searchSize"
          :page-sizes="[5,10,20,50]"
          @current-change="runSourceSearch"
          @size-change="onSourceSearchSize"
        />
      </div>
    </div>

    <!-- 阅读器（内嵌） -->
    <div v-show="tab==='reader'" class="reader-embed">
      <ReaderView
        ref="readerRef"
        embedded
        :initial-paper-id="readerPaperId"
      />
    </div>

    <!-- 导入文献 -->
    <div v-show="tab==='import'" class="import-wrap card">
      <el-alert type="info" :closable="false" style="margin-bottom:14px"
        title="上传 PDF（推荐）/ Word / PPT / TXT。导入在后台解析，完成后会在右上角通知你。扫描版请选 OCR 解析。" />
      <el-upload
        drag
        multiple
        :auto-upload="false"
        :on-change="onFileChange"
        accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md"
      >
        <div class="up-tip">
          <div style="font-size:36px">📤</div>
          <div>拖拽或点击上传（可多选）</div>
          <div class="muted">每个文件自动生成资料卡并解析</div>
        </div>
      </el-upload>
      <el-form style="margin-top:16px" label-width="90px">
        <el-form-item label="类别">
          <el-select v-model="importForm.category" clearable style="width:220px">
            <el-option v-for="c in folderOptions" :key="c.id" :label="c.label" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="importForm.status" style="width:220px">
            <el-option label="想读" value="想读" />
            <el-option label="在读" value="在读" />
            <el-option label="读完" value="读完" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签"><el-input v-model="importForm.tags" placeholder="逗号分隔" style="width:360px" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="importForm.intro" type="textarea" :rows="2" style="width:360px" /></el-form-item>
        <el-form-item label="解析方式">
            <el-radio-group v-model="importForm.parse_mode">
            <el-radio value="ocr">PaddleOCR 版面还原</el-radio>
            <el-radio value="mineru">MinerU 文档解析</el-radio>
            <el-radio value="layout">PDF 内嵌文本解析</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="importing" @click="doImport">后台导入</el-button>
          <span class="muted" style="margin-left:10px">已选 {{ importFiles.length }} 个文件</span>
        </el-form-item>
      </el-form>
    </div>

    <el-dialog v-model="hitImportVisible" :title="hitImportTitle" width="560px" destroy-on-close>
      <div v-if="pendingHits[0]" class="import-preview">
        <div class="import-title">{{ pendingHits[0].title }}</div>
        <div class="muted">
          {{ pendingHits[0].authors }} · {{ pendingHits[0].year || '—' }}
          <span v-if="pendingHits.length > 1"> · 等 {{ pendingHits.length }} 篇</span>
        </div>
      </div>
      <el-form label-width="90px" style="margin-top:16px">
        <el-form-item label="类别" required>
          <el-select v-model="hitImportForm.category" placeholder="请选择文件夹" style="width:100%">
            <el-option v-for="c in folderOptions" :key="c.id" :label="c.label" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="hitImportForm.status" style="width:100%">
            <el-option label="想读" value="想读" />
            <el-option label="在读" value="在读" />
            <el-option label="读完" value="读完" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="hitImportForm.tags" placeholder="逗号分隔，如 OCR, Transformer" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="hitImportForm.intro" type="textarea" :rows="3" placeholder="一句话简介，可改" />
        </el-form-item>
        <el-form-item label="解析方式">
          <el-radio-group v-model="hitImportForm.parse_mode">
            <el-radio value="ocr">PaddleOCR 版面还原</el-radio>
            <el-radio value="mineru">MinerU 文档解析</el-radio>
            <el-radio value="layout">PDF 内嵌文本解析</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="hitImportVisible=false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="confirmHitImport">确认导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="修改文献信息" width="560px" destroy-on-close>
      <div v-if="editing" class="import-preview">
        <div class="import-title">{{ editing.title }}</div>
        <div class="muted">{{ editing.authors }} · {{ editing.year || '—' }}</div>
      </div>
      <el-form label-width="90px" style="margin-top:16px">
        <el-form-item label="类别">
          <el-select v-model="editForm.category" clearable placeholder="请选择文件夹" style="width:100%">
            <el-option v-for="c in folderOptions" :key="c.id" :label="c.label" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width:100%">
            <el-option label="想读" value="想读" />
            <el-option label="在读" value="在读" />
            <el-option label="读完" value="读完" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="editForm.tags" placeholder="逗号分隔，如 OCR, Transformer" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="editForm.intro" type="textarea" :rows="3" placeholder="一句话简介，可改" />
        </el-form-item>
        <el-form-item label="解析方式">
          <el-radio-group v-model="editForm.parse_mode">
            <el-radio value="ocr">PaddleOCR 版面还原</el-radio>
            <el-radio value="mineru">MinerU 文档解析</el-radio>
            <el-radio value="layout">PDF 内嵌文本解析</el-radio>
          </el-radio-group>
          <el-checkbox v-model="editForm.reparse" style="margin-top:8px">保存后按此方式重新解析正文</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible=false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="shareVisible" title="分享论文" width="420px">
      <el-radio-group v-model="shareForm.target_type">
        <el-radio value="user">分享给用户</el-radio>
        <el-radio value="team" :disabled="!canTeamShare">分享给团队</el-radio>
      </el-radio-group>
      <p v-if="!canTeamShare" class="muted" style="margin-top:8px">当前套餐无法团队共享，升级铂金/钻石会员后可用。</p>
      <template v-if="shareForm.target_type==='user'">
        <el-input v-model="userQ" placeholder="搜索昵称" style="margin-top:12px" @input="searchUsers" />
        <div v-for="u in users" :key="u.id" class="user-row" @click="shareForm.target_user_id=u.id">
          {{ u.avatar }} {{ u.username }}
          <el-tag v-if="shareForm.target_user_id===u.id" size="small">已选</el-tag>
        </div>
      </template>
      <el-select v-else v-model="shareForm.target_team_id" placeholder="选择团队" style="width:100%;margin-top:12px">
        <el-option v-for="t in myTeams" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
      <el-input v-model="shareForm.message" type="textarea" placeholder="留言" style="margin-top:12px" />
      <template #footer>
        <el-button @click="shareVisible=false">取消</el-button>
        <el-button type="primary" @click="doShare">分享</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import api from '@/api/http'
import ReaderView from '@/views/ReaderView.vue'
import { buildSummaryView } from '@/utils/paperSummary'
import { SEARCH_SORT_OPTIONS } from '@/utils/searchSort'
import { useNotifyStore } from '@/stores/notify'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const canTeamShare = computed(() => {
  const m = auth.user?.membership
  if (!m) return false
  if (m.unlimited) return true
  return m.team_share_limit < 0 || (m.team_share_left || 0) > 0
})
const tab = ref('mine')
const categories = ref([])
const papers = ref([])
const current = ref(null)
const trash = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const counts = reactive({ all: 0 })
const filters = reactive({ category: null, status: null, search: '', starred: false })
const sources = ref([])
const activeSource = ref(null)
const arxivQ = ref('')
const arxivResults = ref([])
const searching = ref(false)
const searched = ref(false)
const selectedIds = ref([])
const selAll = ref(false)
const searchPage = ref(1)
const searchSize = ref(10)
const searchTotal = ref(0)
const searchSort = ref('relevance')
const searchSortOptions = SEARCH_SORT_OPTIONS
const notifyStore = useNotifyStore()
const hitImportVisible = ref(false)
const pendingHits = ref([])
const hitImportForm = reactive({ category: null, status: '想读', tags: '', intro: '', parse_mode: 'ocr' })
const importFiles = ref([])
const importing = ref(false)
const importingId = ref('')
const importForm = reactive({ category: null, status: '想读', tags: '', intro: '', parse_mode: 'ocr' })
const editVisible = ref(false)
const editSaving = ref(false)
const editing = ref(null)
const editForm = reactive({ category: null, status: '想读', tags: '', intro: '', parse_mode: 'ocr', reparse: false })
const shareVisible = ref(false)
const shareForm = reactive({ target_type: 'user', target_user_id: null, target_team_id: null, message: '' })
const users = ref([])
const userQ = ref('')
const myTeams = ref([])
const readerPaperId = ref(null)
const readerRef = ref(null)
const fetchingPdf = ref(false)
const expandedIds = ref([])
const summaryView = computed(() => buildSummaryView(current.value?.ai_summary))

const folderTree = computed(() => buildFolderTree(categories.value))
const folderFlat = computed(() => {
  const out = []
  const walk = (nodes, depth) => {
    for (const n of nodes) {
      out.push({ ...n, depth })
      if (n.children?.length && expandedIds.value.includes(n.id)) walk(n.children, depth + 1)
    }
  }
  walk(folderTree.value, 0)
  return out
})
const folderOptions = computed(() => {
  const out = []
  const walk = (nodes, prefix) => {
    for (const n of nodes) {
      const label = prefix ? `${prefix} / ${n.name}` : n.name
      out.push({ id: n.id, label })
      if (n.children?.length) walk(n.children, label)
    }
  }
  walk(folderTree.value, '')
  return out
})
const currentFolder = computed(() => categories.value.find((c) => c.id === filters.category) || null)
const breadcrumb = computed(() => folderPath(filters.category))
const emptyHint = computed(() => {
  if (trash.value) return '回收站是空的'
  if (filters.starred) return '还没有收藏的论文'
  if (currentFolder.value) return '此文件夹还是空的，可在右侧新建子文件夹，或去导入文献'
  return '暂无文献，去「收藏网站」或「导入文献」添加'
})

function buildFolderTree(list) {
  const byParent = new Map()
  for (const c of list || []) {
    const pid = c.parent == null ? 0 : c.parent
    if (!byParent.has(pid)) byParent.set(pid, [])
    byParent.get(pid).push(c)
  }
  const kids = (pid) => (byParent.get(pid) || []).map((c) => ({
    ...c,
    children: kids(c.id),
  }))
  return kids(0)
}

function folderPath(id) {
  if (!id) return []
  const map = new Map(categories.value.map((c) => [c.id, c]))
  const path = []
  const seen = new Set()
  let cur = map.get(id)
  while (cur && !seen.has(cur.id)) {
    path.unshift(cur)
    seen.add(cur.id)
    cur = cur.parent ? map.get(cur.parent) : null
  }
  return path
}

function isExpanded(id) {
  return expandedIds.value.includes(id)
}

function toggleExpand(id) {
  if (expandedIds.value.includes(id)) {
    expandedIds.value = expandedIds.value.filter((x) => x !== id)
  } else {
    expandedIds.value = [...expandedIds.value, id]
  }
}

function expandTo(id) {
  const ids = new Set(expandedIds.value)
  for (const c of folderPath(id)) ids.add(c.id)
  expandedIds.value = [...ids]
}

function sourceKind(s) {
  const blob = `${s?.name || ''} ${s?.url || ''} ${s?.icon || ''}`.toLowerCase()
  if (blob.includes('arxiv')) return 'arxiv'
  if (blob.includes('semantic') || blob.includes('s2')) return 's2'
  if (blob.includes('acl') || blob.includes('anthology')) return 'acl'
  if (blob.includes('openreview')) return 'openreview'
  if (blob.includes('baidu') || blob.includes('xueshu')) return 'baidu'
  if (blob.includes('google') || blob.includes('scholar.google')) return 'google'
  return 'web'
}

function isArxiv(s) {
  return sourceKind(s) === 'arxiv'
}

function hitKey(r) {
  return r?.arxiv_id || r?.doi || r?.external_id || r?.id || r?.title || ''
}

const sourcePlaceholder = computed(() => {
  const s = activeSource.value
  if (!s) return '请先选择收藏网站'
  const k = sourceKind(s)
  if (k === 'arxiv') return '搜索关键词 / arXiv ID，如 transformer 或 1706.03762'
  if (k === 's2') return '在 Semantic Scholar 中搜索标题或关键词'
  if (k === 'openreview') return '在 OpenReview 中搜索标题或关键词'
  if (k === 'acl') return '在 ACL Anthology 中搜索标题或关键词'
  return `在「${s.name}」中搜索论文标题或关键词`
})

const sourceTip = computed(() => {
  const k = sourceKind(activeSource.value)
  if (k === 's2') {
    return 'Semantic Scholar 有请求频率限制，繁忙时自动改用开放学术索引。有开放 PDF 时导入会自动下载并解析。'
  }
  if (k === 'baidu' || k === 'google' || k === 'web') {
    return '该网站无公开检索接口，已接入 OpenAlex / Crossref 开放学术索引，可检索并导入开放获取 PDF。'
  }
  return '在站内检索收藏网站，勾选后导入；有开放 PDF 时会自动下载并解析正文。'
})

const hitImportTitle = computed(() => {
  const n = pendingHits.value.length
  return n > 1 ? `导入 ${n} 篇文献` : '导入文献库'
})

function selectSource(s) {
  activeSource.value = s
  arxivResults.value = []
  searched.value = false
  selectedIds.value = []
  selAll.value = false
  searchTotal.value = 0
  searchPage.value = 1
}

function pickArxiv() {
  const s = sources.value.find(isArxiv)
  if (s) selectSource(s)
}

async function loadCategories() {
  const rows = await api.get('/papers/categories/')
  categories.value = Array.isArray(rows) ? rows : (rows.results || [])
  try {
    const data = await api.get('/papers/', { params: { page: 1, page_size: 1 } })
    counts.all = data.count || 0
  } catch {
    counts.all = categories.value.reduce((s, c) => s + (c.paper_count || 0), 0)
  }
}

function onPaperFilter() {
  page.value = 1
  loadPapers()
}

function onPaperSize() {
  page.value = 1
  loadPapers()
}

async function createFolder(parentId) {
  const pid = typeof parentId === 'number' ? parentId : filters.category
  const parent = pid ? categories.value.find((c) => c.id === pid) : null
  try {
    const { value } = await ElMessageBox.prompt(
      parent ? `在「${parent.name}」内新建子文件夹` : '新建文件夹（出现在左侧目录）',
      '新建文件夹',
      { inputPlaceholder: '文件夹名称', confirmButtonText: '创建', cancelButtonText: '取消', inputValue: '' },
    )
    const name = String(value || '').trim()
    if (!name) return
    await api.post('/papers/categories/', { name, parent: pid || null })
    if (pid) expandTo(pid)
    ElMessage.success('已创建文件夹')
    await loadCategories()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e.message || '创建失败')
  }
}

async function renameFolder(f) {
  try {
    const { value } = await ElMessageBox.prompt('文件夹名称', '重命名', {
      inputValue: f.name,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    const name = String(value || '').trim()
    if (!name || name === f.name) return
    await api.patch(`/papers/categories/${f.id}/`, { name })
    ElMessage.success('已重命名')
    await loadCategories()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    ElMessage.error(e.message || '重命名失败')
  }
}

async function deleteFolder(f) {
  await ElMessageBox.confirm(`删除文件夹「${f.name}」？其中的论文不会删除，子文件夹需先删掉。`, '删除文件夹', { type: 'warning' })
  await api.delete(`/papers/categories/${f.id}/`)
  ElMessage.success('已删除')
  if (filters.category === f.id) setFolder()
  else await loadCategories()
}

async function onFolderMenu(f) {
  try {
    await ElMessageBox.confirm(`对文件夹「${f.name}」执行操作`, '文件夹', {
      distinguishCancelAndClose: true,
      confirmButtonText: '重命名',
      cancelButtonText: '删除',
      type: 'info',
    })
    await renameFolder(f)
  } catch (action) {
    if (action === 'cancel') {
      try {
        await deleteFolder(f)
      } catch (e) {
        if (e === 'cancel' || e === 'close') return
        ElMessage.error(e.message || '删除失败')
      }
    }
  }
}

async function loadPapers() {
  const params = {
    page: page.value,
    page_size: pageSize.value,
    trash: trash.value ? 1 : undefined,
    category: filters.category || undefined,
    status: filters.status || undefined,
    starred: filters.starred || undefined,
    search: filters.search || undefined,
  }
  const data = await api.get('/papers/', { params })
  papers.value = data.results || data
  total.value = data.count || papers.value.length
}

async function select(p) {
  current.value = await api.get(`/papers/${p.id}/`)
}

function openEdit(p) {
  if (trash.value) return
  editing.value = p
  editForm.category = p.category || null
  editForm.status = p.status || '想读'
  editForm.tags = p.tags || ''
  editForm.intro = p.intro || ''
  editForm.parse_mode = 'ocr'
  editForm.reparse = false
  editVisible.value = true
  select(p)
}

async function saveEdit() {
  if (!editing.value) return
  editSaving.value = true
  try {
    await api.patch(`/papers/${editing.value.id}/`, {
      category: editForm.category || null,
      status: editForm.status,
      tags: editForm.tags,
      intro: editForm.intro,
    })
    if (editForm.reparse) {
      try {
        await api.post(`/papers/${editing.value.id}/reparse/`, { parse_mode: editForm.parse_mode })
        ElMessage.success('已更新并重新解析')
      } catch (e) {
        ElMessage.warning(`信息已保存，但重新解析失败：${e.message || '请确认已有 PDF'}`)
      }
    } else {
      ElMessage.success('已更新文献信息')
    }
    editVisible.value = false
    await loadPapers()
    await loadCategories()
    if (current.value?.id === editing.value.id) {
      current.value = await api.get(`/papers/${editing.value.id}/`)
    }
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    editSaving.value = false
  }
}

function setFolder(id = null) {
  trash.value = false
  filters.starred = false
  filters.category = id
  page.value = 1
  current.value = null
  if (id) expandTo(id)
  loadPapers()
}
function setStarred() {
  trash.value = false
  filters.category = null
  filters.starred = true
  page.value = 1
  loadPapers()
}
function setTrash() {
  trash.value = true
  filters.category = null
  filters.starred = false
  page.value = 1
  loadPapers()
}

function read(p) {
  readerPaperId.value = p.id
  tab.value = 'reader'
  router.replace({ query: { ...route.query, tab: 'reader', p: p.id } })
  nextTick(() => readerRef.value?.loadPaper?.(p.id))
}

async function remove(p) {
  await ElMessageBox.confirm('移入回收站？', '确认')
  await api.delete(`/papers/${p.id}/`)
  ElMessage.success('已移入回收站')
  current.value = null
  loadPapers(); loadCategories()
}
async function restore(p) {
  await api.post(`/papers/${p.id}/restore/`)
  ElMessage.success('已恢复')
  loadPapers(); loadCategories()
}
async function purge(p) {
  await ElMessageBox.confirm('彻底删除不可恢复', '危险操作', { type: 'warning' })
  await api.delete(`/papers/${p.id}/purge/`)
  ElMessage.success('已删除')
  loadPapers()
}

async function toggleStar() {
  current.value = await api.patch(`/papers/${current.value.id}/`, { starred: !current.value.starred })
  loadPapers()
}

async function fetchPdf(p) {
  fetchingPdf.value = true
  try {
    current.value = await api.post(`/papers/${p.id}/fetch-pdf/`)
    ElMessage.success('PDF 已解析')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    fetchingPdf.value = false
  }
}

async function loadSources() {
  sources.value = await api.get('/papers/sources/')
  activeSource.value = sources.value.find(isArxiv) || sources.value[0]
}

async function searchSource() {
  if (!arxivQ.value.trim()) return ElMessage.warning('请输入关键词')
  if (!activeSource.value?.id) return ElMessage.warning('请先选择收藏网站')
  searchPage.value = 1
  await runSourceSearch()
}

function onSourceSearchSize() {
  searchPage.value = 1
  runSourceSearch()
}

function onSearchSort() {
  if (!searched.value) return
  searchPage.value = 1
  runSourceSearch()
}

async function runSourceSearch() {
  const kw = arxivQ.value.trim()
  if (!kw) return
  if (!activeSource.value?.id) return ElMessage.warning('请先选择收藏网站')
  searching.value = true
  searched.value = true
  selectedIds.value = []
  selAll.value = false
  try {
    const data = await api.get('/papers/sources/search/', {
      params: {
        q: kw,
        source_id: activeSource.value.id,
        page: searchPage.value,
        page_size: searchSize.value,
        sort: searchSort.value,
      },
    })
    arxivResults.value = data.results || []
    searchTotal.value = data.count || 0
  } catch (e) {
    arxivResults.value = []
    searchTotal.value = 0
    ElMessage.error(e.message || '检索失败，请检查网络')
  } finally {
    searching.value = false
  }
}

function toggleSel(id, checked) {
  if (checked) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
  } else {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  }
  const selectable = arxivResults.value.filter(r => !r.in_library)
  selAll.value = selectable.length > 0 && selectable.every(r => selectedIds.value.includes(hitKey(r)))
}

function toggleSelAll(v) {
  selectedIds.value = v ? arxivResults.value.filter(r => !r.in_library).map(hitKey) : []
}

function openHit(r) {
  if (r.abs_url) window.open(r.abs_url, '_blank')
  else if (r.doi) window.open(`https://doi.org/${r.doi}`, '_blank')
}

function openHitImport(list) {
  const hits = (list || []).filter(r => r && (r.title || r.arxiv_id) && !r.in_library)
  if (!hits.length) return ElMessage.warning('没有可导入的结果')
  pendingHits.value = hits
  hitImportForm.category = null
  hitImportForm.status = '想读'
  hitImportForm.tags = hits[0].category || ''
  hitImportForm.intro = (hits[0].intro || hits[0].abstract || '').slice(0, 400)
  hitImportForm.parse_mode = 'ocr'
  hitImportVisible.value = true
}

function importSelected() {
  const list = arxivResults.value.filter(r => selectedIds.value.includes(hitKey(r)))
  openHitImport(list)
}

function markHitsImported(hits, paper) {
  const id = paper?.id
  const keys = new Set(hits.map(hitKey))
  arxivResults.value.forEach((row) => {
    if (keys.has(hitKey(row))) {
      row.in_library = true
      row.paper_id = id || row.paper_id
    }
  })
}

function watchImportJob(jobId, title, paperId) {
  notifyStore.watchJob(jobId, title, paperId)
}

async function importOneHit(r) {
  const data = await api.post('/papers/import-hit/', {
    arxiv_id: r.arxiv_id || '',
    pdf_url: r.pdf_url,
    title: r.title,
    authors: r.authors,
    year: r.year,
    doi: r.doi,
    abstract: r.abstract,
    venue: r.venue,
    cites: r.cites || 0,
    download_pdf: 1,
    background: 1,
    category: hitImportForm.category,
    status: hitImportForm.status,
    tags: hitImportForm.tags,
    intro: pendingHits.value.length === 1 ? hitImportForm.intro : (hitImportForm.intro || (r.intro || r.abstract || '').slice(0, 400)),
    parse_mode: hitImportForm.parse_mode,
  })
  markHitsImported([r], data)
  const title = (r.title || '论文').slice(0, 60)
  if (data.already && !data.queued) {
    ElNotification({ type: 'info', title: '已在文献库', message: `《${title}》无需重复导入`, duration: 3500 })
  } else if (data.queued && data.job_id) {
    ElNotification({
      type: 'info',
      title: '已开始后台导入',
      message: `《${title}》正在解析，完成后会在右上角通知你`,
      duration: 4500,
    })
    watchImportJob(data.job_id, title, data.id)
  } else {
    ElNotification({ type: 'success', title: '导入成功', message: `《${title}》已加入文献库`, duration: 3500 })
  }
  return data
}

async function confirmHitImport() {
  const hits = pendingHits.value || []
  if (!hits.length) return
  if (!hitImportForm.category) return ElMessage.warning('请选择论文分类')
  importing.value = true
  importingId.value = hits.length === 1 ? hitKey(hits[0]) : 'batch'
  let ok = 0
  let last = null
  try {
    for (const r of hits) {
      importingId.value = hitKey(r)
      try {
        last = await importOneHit(r)
        ok += 1
      } catch (e) {
        ElMessage.error(e.message || `《${(r.title || '').slice(0, 40)}》导入失败`)
      }
    }
    hitImportVisible.value = false
    selectedIds.value = []
    selAll.value = false
    await loadPapers()
    await loadCategories()
    if (hits.length > 1) ElMessage.success(`成功导入 ${ok}/${hits.length} 篇`)
    if (ok === 1 && last?.id && !last.queued) read(last)
  } finally {
    importingId.value = ''
    importing.value = false
  }
}

function onFileChange(file, fileList) {
  importFiles.value = fileList.map(f => f.raw).filter(Boolean)
}

async function doImport() {
  if (!importFiles.value.length) return ElMessage.warning('请选择 PDF 等文件')
  importing.value = true
  try {
    const fd = new FormData()
    importFiles.value.forEach(f => fd.append('files', f))
    if (importForm.category) fd.append('category', importForm.category)
    fd.append('status', importForm.status)
    fd.append('tags', importForm.tags)
    fd.append('intro', importForm.intro)
    fd.append('parse_mode', importForm.parse_mode)
    fd.append('background', '1')
    const data = await api.post('/papers/import-file/', fd)
    const results = Array.isArray(data) ? data : (data?.results || [])
    const queued = results.filter((r) => r.queued && r.job_id)
    queued.forEach((r) => notifyStore.watchJob(r.job_id, r.title, r.id))
    if (queued.length) {
      ElNotification({
        type: 'info',
        title: '已开始后台导入',
        message: `正在解析 ${queued.length} 篇，完成后会在右上角通知你`,
        duration: 5000,
      })
    } else {
      ElMessage.success(`已导入 ${results.length || 1} 篇`)
    }
    importFiles.value = []
    await loadPapers()
    await loadCategories()
    tab.value = 'mine'
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    importing.value = false
  }
}

async function openShare() {
  shareVisible.value = true
  myTeams.value = await api.get('/teams/mine/')
}

async function searchUsers() {
  if (!userQ.value) return
  users.value = await api.get('/auth/users/search/', { params: { q: userQ.value } })
}

async function doShare() {
  await api.post(`/papers/${current.value.id}/share/`, shareForm)
  ElMessage.success('分享成功')
  shareVisible.value = false
}

function onTabChange(name) {
  router.replace({ query: { ...route.query, tab: name } })
  if (name === 'sources') loadSources()
  if (name === 'reader') nextTick(() => readerRef.value?.loadList?.())
}

watch(tab, (v) => { if (v === 'sources') loadSources() })

onMounted(async () => {
  await loadCategories()
  await loadPapers()
  const qTab = route.query.tab
  if (qTab) tab.value = String(qTab)
  if (route.query.p) {
    const id = Number(route.query.p)
    try {
      current.value = await api.get(`/papers/${id}/`)
      if (tab.value === 'reader' || route.query.tab === 'reader') {
        readerPaperId.value = id
        tab.value = 'reader'
      }
    } catch { /* ignore */ }
  }
  if (tab.value === 'sources') await loadSources()
})
</script>

<style scoped>
.lib { padding: 8px 16px 12px; height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.tabs { flex: none; }
.mine-layout {
  flex: 1; min-height: 0; display: grid;
  grid-template-columns: 240px 1fr 300px; gap: 12px; overflow: hidden;
}
.side, .list, .detail { overflow-y: auto; min-height: 0; }
.side { padding: 10px; height: fit-content; max-height: 100%; }
.side-item {
  padding: 7px 8px; border-radius: 8px; cursor: pointer; color: var(--text-2);
  display: flex; align-items: center; gap: 4px;
}
.side-item:hover, .side-item.active { background: var(--primary-light); color: var(--primary); }
.side-item .fname { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.side-item .cnt { margin-left: auto; font-size: 11px; color: var(--text-3); flex: none; }
.twist, .twist-sp {
  width: 16px; flex: none; border: 0; background: none; cursor: pointer;
  color: inherit; padding: 0; line-height: 1;
}
.crumb { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin-bottom: 8px; font-size: 13px; }
.crumb-link {
  border: 0; background: none; color: var(--primary); cursor: pointer; padding: 0;
}
.crumb-link.current { color: var(--text); font-weight: 650; cursor: default; }
.crumb-sep { color: var(--text-3); }
.folder-pane { padding: 28px 8px; text-align: center; }
.folder-hero { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.pager { margin-top: 14px; width: 100%; justify-content: center; }
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.hint { font-size: 12px; margin-left: 4px; }
.row { display: flex; gap: 12px; align-items: center; margin-bottom: 10px; }
.grow { flex: 1; min-width: 0; }
.title { font-weight: 600; }
.title.trash { text-decoration: line-through; color: var(--text-3); }
.intro-tag {
  margin-top: 4px; font-size: 12.5px; color: #92400e; background: #fffbeb;
  border: 1px solid #fde68a; border-radius: 6px; padding: 2px 8px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.meta { display: flex; gap: 8px; align-items: center; margin-top: 6px; flex-wrap: wrap; }
.detail { padding: 16px; }
.summary { margin-top: 12px; padding: 10px; background: var(--primary-light); border-radius: 8px; }
.summary h4 { margin: 0 0 8px; font-size: 14px; }
.sum-sec { margin-bottom: 10px; }
.sum-sec h5 { margin: 0 0 4px; font-size: 12px; color: var(--primary); font-weight: 700; }
.sum-zh { margin: 0; font-size: 13px; line-height: 1.55; white-space: pre-wrap; }
.sum-en { margin: 4px 0 0; font-size: 12px; line-height: 1.5; color: var(--text-2); white-space: pre-wrap; }
.sum-term { margin: 0 0 4px; font-size: 12.5px; }
.import-preview {
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 10px;
}
.import-title { font-weight: 650; font-size: 15px; line-height: 1.45; margin-bottom: 4px; }
.abs { margin-top: 12px; color: var(--text-2); font-size: 13px; max-height: 180px; overflow: auto; }
.sources-wrap, .import-wrap { flex: 1; overflow-y: auto; padding: 8px 4px 20px; }
.import-wrap { padding: 20px; }
.section-tip { margin-bottom: 10px; }
.sources { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
.src { padding: 14px; cursor: pointer; }
.src.active { border-color: var(--primary); background: var(--primary-light); }
.sel-bar { display: flex; gap: 12px; align-items: center; margin: 12px 0 4px; }
.arxiv-item {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 0; border-bottom: 1px solid var(--border);
}
.adaptor-empty { padding: 48px 20px; text-align: center; color: var(--text-2); }
.reader-embed { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.reader-embed :deep(.reader) { flex: 1; min-height: 0; height: 100%; }
.up-tip { padding: 20px; text-align: center; }
.user-row { padding: 8px; cursor: pointer; border-radius: 6px; }
.user-row:hover { background: var(--primary-light); }
@media (max-width: 960px) {
  .mine-layout { grid-template-columns: 1fr; overflow: auto; }
}
</style>
