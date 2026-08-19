<template>
  <div class="discover">
    <div class="hero card">
      <h2>发现好论文</h2>
      <p class="hero-sub">从你的收藏网站检索论文，默认 arXiv</p>
      <form class="search-row" @submit.prevent="doSearch">
        <el-select
          v-model="sourceId"
          size="large"
          class="source-select"
          placeholder="收藏网站"
          @change="onSourcePick"
        >
          <el-option v-for="s in sources" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-input
          v-model="q"
          size="large"
          :placeholder="searchPlaceholder"
          clearable
          @keyup.enter.prevent="doSearch"
          @clear="clearSearch"
        >
          <template #append>
            <el-button native-type="submit" :loading="searching">搜索</el-button>
          </template>
        </el-input>
      </form>
      <div class="hot-words">
        <span class="muted">热门：</span>
        <span v-for="w in hotWords" :key="w" class="tag" @click="searchHotWord(w)">{{ w }}</span>
      </div>
    </div>

    <section v-if="searched" class="block">
      <div class="head">
        <span class="h">搜索结果</span>
        <span class="muted">来源 {{ resultSourceName }} · 共 {{ searchTotal }} 篇</span>
        <el-select v-model="searchSort" size="small" style="width:158px" @change="onSearchSort">
          <el-option v-for="o in recSortOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <button type="button" class="link-btn" @click="clearSearch">返回推荐</button>
      </div>
      <div v-if="searching && !searchList.length" class="empty">正在检索…</div>
      <div v-else-if="!searchList.length" class="empty">没有匹配结果，换个关键词试试</div>
      <div v-else class="grid">
        <PaperHit
          v-for="p in searchList"
          :key="p.arxiv_id || p.doi || p.id || p.title"
          :p="p"
          :busy-id="importingId"
          @import="importPaper"
          @read="goRead"
          @open="goOpen"
        />
      </div>
      <el-pagination
        v-if="searchTotal > searchSize"
        class="pager"
        layout="total, prev, pager, next, sizes, jumper"
        :total="searchTotal"
        v-model:current-page="searchPage"
        v-model:page-size="searchSize"
        :page-sizes="[5,10,20,50]"
        @current-change="runSearch"
        @size-change="onSearchSize"
      />
    </section>

    <div v-else class="cols">
      <section class="block">
        <div class="head">
          <span class="h">为你推荐</span>
          <span class="muted">{{ recHint }}</span>
          <div class="filters">
            <el-select v-model="recYear" size="small" style="width:118px" @change="onRecFilter">
              <el-option v-for="o in yearOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
            <el-select v-model="recCites" size="small" style="width:118px" @change="onRecFilter">
              <el-option v-for="o in citeOptions" :key="String(o.value)" :label="o.label" :value="o.value" />
            </el-select>
            <el-select v-model="recSort" size="small" style="width:128px" @change="onRecFilter">
              <el-option v-for="o in recSortOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </div>
        </div>
        <div v-if="recLoading && !recList.length" class="empty">正在根据你的方向生成推荐…</div>
        <div v-else-if="!recList.length" class="empty">暂时没有推荐，先去个人中心填写研究方向，或读几篇论文</div>
        <div v-else class="list">
          <PaperHit
            v-for="p in recList"
            :key="p.arxiv_id || p.doi || p.id || p.title"
            :p="p"
            :busy-id="importingId"
            @import="importPaper"
            @read="goRead"
            @open="goOpen"
          />
        </div>
        <el-pagination
          v-if="recTotal > recSize"
          class="pager"
          layout="total, prev, pager, next, sizes"
          :total="recTotal"
          v-model:current-page="recPage"
          v-model:page-size="recSize"
          :page-sizes="[5,10,20]"
          @current-change="loadRecommend"
          @size-change="onRecSize"
        />
      </section>

      <section class="block">
        <div class="head">
          <span class="h">热门论文</span>
          <span class="muted">可按年份、引用量筛选排序</span>
          <div class="filters">
            <el-select v-model="hotYear" size="small" style="width:118px" @change="onHotFilter">
              <el-option v-for="o in yearOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
            <el-select v-model="hotCites" size="small" style="width:118px" @change="onHotFilter">
              <el-option v-for="o in citeOptions" :key="'h'+o.value" :label="o.label" :value="o.value" />
            </el-select>
            <el-select v-model="hotSort" size="small" style="width:128px" @change="onHotFilter">
              <el-option v-for="o in hotSortOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </div>
        </div>
        <div v-if="hotLoading && !hotList.length" class="empty">加载热门…</div>
        <div v-else-if="!hotList.length" class="empty">暂无热门数据</div>
        <div v-else class="list">
          <PaperHit
            v-for="p in hotList"
            :key="(p.arxiv_id || p.id) + '-' + p.rank"
            :p="p"
            :rank="p.rank"
            :busy-id="importingId"
            @import="importPaper"
            @read="goRead"
            @open="goOpen"
          />
        </div>
        <el-pagination
          v-if="hotTotal > hotSize"
          class="pager"
          layout="total, prev, pager, next, sizes"
          :total="hotTotal"
          v-model:current-page="hotPage"
          v-model:page-size="hotSize"
          :page-sizes="[5,10,20]"
          @current-change="loadHot"
          @size-change="onHotSize"
        />
      </section>
    </div>

    <el-dialog v-model="importVisible" title="导入文献库" width="560px" destroy-on-close>
      <div v-if="pending" class="import-preview">
        <div class="import-title">{{ pending.title }}</div>
        <div class="muted">{{ pending.authors }} · {{ pending.year || '—' }} · {{ pending.arxiv_id }}</div>
      </div>
      <el-form label-width="90px" style="margin-top:16px">
        <el-form-item label="类别" required>
          <el-select v-model="importForm.category" placeholder="请选择文件夹" style="width:100%">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.label" :value="c.id" />
          </el-select>
          <div v-if="!categories.length" class="muted" style="margin-top:6px">暂无文件夹，请先到文献库新建</div>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="importForm.status" style="width:100%">
            <el-option label="想读" value="想读" />
            <el-option label="在读" value="在读" />
            <el-option label="读完" value="读完" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="importForm.tags" placeholder="逗号分隔，如 OCR, Transformer" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="importForm.intro" type="textarea" :rows="3" placeholder="一句话简介，可改" />
        </el-form-item>
        <el-form-item label="解析方式">
          <el-radio-group v-model="importForm.parse_mode">
            <el-radio value="ocr">PaddleOCR 版面还原</el-radio>
            <el-radio value="mineru">MinerU 文档解析</el-radio>
            <el-radio value="layout">PDF 内嵌文本解析</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible=false">取消</el-button>
        <el-button type="primary" :loading="!!importingId" @click="confirmImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import api from '@/api/http'
import PaperHit from '@/components/PaperHit.vue'
import { useNotifyStore } from '@/stores/notify'

const router = useRouter()
const q = ref('')
const sources = ref([])
const sourceId = ref(null)
const searchSourceName = ref('')
const searched = ref(false)
const searching = ref(false)
const searchList = ref([])
const searchTotal = ref(0)
const searchPage = ref(1)
const searchSize = ref(10)
const searchSort = ref('relevance')
const notifyStore = useNotifyStore()

const recList = ref([])
const recTotal = ref(0)
const recPage = ref(1)
const recSize = ref(5)
const recLoading = ref(false)
const recHint = ref('根据研究方向、最近阅读和笔记兴趣')
const recYear = ref('')
const recCites = ref(0)
const recSort = ref('relevance')

const hotList = ref([])
const hotTotal = ref(0)
const hotPage = ref(1)
const hotSize = ref(5)
const hotLoading = ref(false)
const hotYear = ref('')
const hotCites = ref(0)
const hotSort = ref('cites')

const yearNow = new Date().getFullYear()
const yearOptions = [
  { label: '全部年份', value: '' },
  { label: `${yearNow} 年`, value: String(yearNow) },
  { label: `${yearNow - 1} 年`, value: String(yearNow - 1) },
  { label: `${yearNow - 2} 年`, value: String(yearNow - 2) },
  { label: '近三年', value: '3y' },
  { label: '近五年', value: '5y' },
  { label: '2018 以来', value: '2018+' },
]
const citeOptions = [
  { label: '引用不限', value: 0 },
  { label: '≥ 100', value: 100 },
  { label: '≥ 1,000', value: 1000 },
  { label: '≥ 1 万', value: 10000 },
]
const recSortOptions = [
  { label: '相关度', value: 'relevance' },
  { label: '最新发表', value: 'newest' },
  { label: '年份从新到旧', value: 'year' },
  { label: '年份从旧到新', value: 'year_asc' },
  { label: '引用量从高到低', value: 'cites' },
]
const hotSortOptions = [
  { label: '引用量从高到低', value: 'cites' },
  { label: '最新发表', value: 'newest' },
  { label: '年份从新到旧', value: 'year' },
  { label: '年份从旧到新', value: 'year_asc' },
]

const importingId = ref('')
const importVisible = ref(false)
const pending = ref(null)
const categories = ref([])
const categoryOptions = computed(() => {
  const list = categories.value || []
  const byId = new Map(list.map((c) => [c.id, c]))
  const labelOf = (c) => {
    const parts = [c.name]
    const seen = new Set([c.id])
    let p = c.parent ? byId.get(c.parent) : null
    while (p && !seen.has(p.id)) {
      parts.unshift(p.name)
      seen.add(p.id)
      p = p.parent ? byId.get(p.parent) : null
    }
    return parts.join(' / ')
  }
  return list.map((c) => ({ id: c.id, label: labelOf(c) }))
})
const importForm = reactive({
  category: null,
  status: '想读',
  tags: '',
  intro: '',
  parse_mode: 'ocr',
})
const hotWords = ['Transformer', 'OCR', 'ResNet', 'ViT', 'DETR']

function toSourceId(v) {
  const n = Number(v)
  return Number.isFinite(n) && n > 0 ? n : null
}

function findSource(id) {
  const sid = toSourceId(id)
  if (!sid) return null
  return sources.value.find((s) => toSourceId(s.id) === sid) || null
}

const currentSource = computed(() => findSource(sourceId.value))
const currentSourceName = computed(() => currentSource.value?.name || '')
const resultSourceName = computed(() => searchSourceName.value || currentSourceName.value || '当前来源')
const searchPlaceholder = computed(() => {
  const name = currentSourceName.value
  if (!name) return '输入论文标题或关键词'
  if (/arxiv/i.test(name)) return '标题 / 关键词 / arXiv ID，如 transformer 或 1706.03762'
  return `在「${name}」中搜索论文标题或关键词`
})

function isArxivSource(s) {
  if (!s) return false
  return /arxiv/i.test(`${s.name || ''} ${s.url || ''} ${s.icon || ''}`)
}

function setSourceId(id) {
  const sid = toSourceId(id)
  if (!sid) return
  sourceId.value = sid
}

function pickArxiv() {
  const s = sources.value.find(isArxivSource)
  if (s) setSourceId(s.id)
}

function onSourcePick(v) {
  setSourceId(v)
}

function searchHotWord(w) {
  q.value = w
  doSearch()
}

async function loadSources() {
  try {
    const rows = await api.get('/papers/sources/')
    const list = Array.isArray(rows) ? rows : (rows.results || [])
    sources.value = list.map((s) => ({ ...s, id: toSourceId(s.id) }))
    const keep = findSource(sourceId.value)
    if (keep) {
      setSourceId(keep.id)
      return
    }
    pickArxiv()
    if (!sourceId.value && sources.value[0]) setSourceId(sources.value[0].id)
  } catch {
    sources.value = []
  }
}

async function doSearch() {
  const kw = q.value.trim()
  if (!kw) return ElMessage.warning('请输入关键词')
  searched.value = true
  searchPage.value = 1
  await runSearch()
}

function onSearchSize() {
  searchPage.value = 1
  runSearch()
}

function onSearchSort() {
  searchPage.value = 1
  runSearch()
}

async function runSearch() {
  const kw = q.value.trim()
  const sid = toSourceId(sourceId.value)
  if (!kw) return
  if (!sid) return ElMessage.warning('请先选择收藏网站')
  searching.value = true
  try {
    const data = await api.get('/papers/sources/search/', {
      params: {
        q: kw,
        source_id: sid,
        page: searchPage.value,
        page_size: searchSize.value,
        sort: searchSort.value,
      },
    })
    searchList.value = data.results || []
    searchTotal.value = data.count || 0
    searchSourceName.value = data.source_name || findSource(sid)?.name || ''
  } catch (e) {
    ElMessage.error(e.message || '搜索失败')
  } finally {
    setSourceId(sid)
    searching.value = false
  }
}

function clearSearch() {
  searched.value = false
  searchList.value = []
  searchTotal.value = 0
  searchSourceName.value = ''
}

function onRecSize() {
  recPage.value = 1
  loadRecommend()
}
function onHotSize() {
  hotPage.value = 1
  loadHot()
}
function onRecFilter() {
  recPage.value = 1
  loadRecommend()
}
function onHotFilter() {
  hotPage.value = 1
  loadHot()
}

function yearRange(preset) {
  if (!preset) return {}
  if (preset === '3y') return { year_from: yearNow - 2, year_to: yearNow }
  if (preset === '5y') return { year_from: yearNow - 4, year_to: yearNow }
  if (String(preset).endsWith('+')) {
    const n = Number(String(preset).replace('+', ''))
    return Number.isFinite(n) ? { year_from: n, year_to: yearNow } : {}
  }
  const n = Number(preset)
  return Number.isFinite(n) ? { year_from: n, year_to: n } : {}
}

function listQuery(yearPreset, minCites, sort, page, pageSize) {
  return {
    page,
    page_size: pageSize,
    sort,
    min_cites: minCites || undefined,
    ...yearRange(yearPreset),
  }
}

async function loadRecommend() {
  recLoading.value = true
  try {
    const data = await api.get('/papers/discover/recommend/', {
      params: listQuery(recYear.value, recCites.value, recSort.value, recPage.value, recSize.value),
    })
    recList.value = data.results || []
    recTotal.value = data.count || 0
    if (data.reasons?.length) recHint.value = data.reasons.join(' · ')
  } catch (e) {
    ElMessage.error(e.message || '推荐加载失败')
  } finally {
    recLoading.value = false
  }
}

async function loadHot() {
  hotLoading.value = true
  try {
    const data = await api.get('/papers/discover/hot/', {
      params: listQuery(hotYear.value, hotCites.value, hotSort.value, hotPage.value, hotSize.value),
    })
    hotList.value = data.results || []
    hotTotal.value = data.count || 0
  } catch (e) {
    ElMessage.error(e.message || '热门加载失败')
  } finally {
    hotLoading.value = false
  }
}

function markImported(p, paper) {
  const id = paper?.id
  const aid = p.arxiv_id
  const doi = (p.doi || '').toLowerCase()
  const title = (p.title || '').toLowerCase()
  const patch = (row) => {
    const hit = (aid && row.arxiv_id === aid)
      || (doi && (row.doi || '').toLowerCase() === doi)
      || (title && (row.title || '').toLowerCase() === title)
    if (hit) {
      row.in_library = true
      row.paper_id = id
    }
  }
  recList.value.forEach(patch)
  hotList.value.forEach(patch)
  searchList.value.forEach(patch)
}

async function importPaper(p) {
  if (!p.arxiv_id && !p.title) {
    ElMessage.warning('无法导入这条结果')
    return
  }
  if (!categories.value.length) {
    await loadCategories()
  }
  pending.value = p
  importForm.category = null
  importForm.status = '想读'
  importForm.tags = p.category || ''
  importForm.intro = (p.intro || p.abstract || '').slice(0, 400)
  importForm.parse_mode = 'ocr'
  importVisible.value = true
}

async function confirmImport() {
  const p = pending.value
  if (!p?.title) return
  if (!importForm.category) {
    ElMessage.warning('请选择论文分类')
    return
  }
  importingId.value = p.arxiv_id || p.doi || p.title
  try {
    const data = await api.post('/papers/import-hit/', {
      arxiv_id: p.arxiv_id || '',
      pdf_url: p.pdf_url,
      title: p.title,
      authors: p.authors,
      year: p.year,
      doi: p.doi,
      abstract: p.abstract,
      venue: p.venue,
      cites: p.cites || 0,
      download_pdf: 1,
      background: 1,
      category: importForm.category,
      status: importForm.status,
      tags: importForm.tags,
      intro: importForm.intro,
      parse_mode: importForm.parse_mode,
    })
    markImported(p, data)
    importVisible.value = false
    const title = (p.title || '论文').slice(0, 60)
    if (data.already) {
      ElNotification({ type: 'info', title: '已在文献库', message: `《${title}》无需重复导入`, duration: 4500 })
    } else if (data.queued && data.job_id) {
      ElNotification({
        type: 'info',
        title: '已开始后台导入',
        message: `《${title}》正在解析，完成后会在右上角通知你`,
        duration: 4500,
      })
      notifyStore.watchJob(data.job_id, title, data.id)
    } else {
      ElNotification({ type: 'success', title: '导入成功', message: `《${title}》已加入文献库`, duration: 4500 })
    }
  } catch (e) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    importingId.value = ''
  }
}

async function loadCategories() {
  try {
    categories.value = await api.get('/papers/categories/') || []
  } catch {
    categories.value = []
  }
}

function goOpen(p) {
  if (p.in_library || p.paper_id) {
    router.push({ name: 'library', query: { p: p.paper_id || p.id } })
    return
  }
  if (p.abs_url) window.open(p.abs_url, '_blank')
  else if (p.doi) window.open(`https://doi.org/${p.doi}`, '_blank')
}

function goRead(p) {
  const id = p.paper_id || p.id
  if (!id) return importPaper(p)
  router.push({ name: 'library', query: { tab: 'reader', p: id } })
}

onMounted(() => {
  loadSources()
  loadCategories()
  loadRecommend()
  loadHot()
})
</script>

<style scoped>
.discover {
  padding: 8px 16px 16px;
  width: 100%;
  max-width: none;
  height: 100%;
  box-sizing: border-box;
}
.hero { padding: 28px; margin-bottom: 20px; background: linear-gradient(135deg, #eff6ff, #f5f3ff); }
.hero h2 { margin-bottom: 6px; }
.hero-sub { color: var(--text-2); font-size: 13.5px; margin-bottom: 14px; }
.search-row { display: flex; gap: 10px; align-items: center; }
.search-row :deep(.el-input) { flex: 1; }
.source-select { width: 190px; flex: none; }
.hot-words { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.tag {
  padding: 2px 10px; border-radius: 999px; background: #f3f4f6; color: var(--text-2);
  cursor: pointer; font-size: 12px;
}
.tag:hover { background: var(--primary-light); color: var(--primary); }
.head {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin: 8px 0 14px;
}
.head .h { font-size: 16px; font-weight: 700; }
.filters { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
.link-btn {
  margin-left: auto; border: 0; background: none; color: var(--primary); cursor: pointer; font-size: 13px;
}
.cols {
  display: flex;
  flex-direction: column;
  gap: 28px;
}
.block { min-width: 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 14px; }
.list { display: flex; flex-direction: column; gap: 14px; }
.empty { padding: 28px 12px; text-align: center; color: var(--text-3); font-size: 13px; }
.pager { margin-top: 14px; width: 100%; justify-content: center; }
.import-preview {
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 10px;
}
.import-title { font-weight: 650; font-size: 15px; line-height: 1.45; margin-bottom: 4px; }
@media (max-width: 960px) {
  .search-row { flex-direction: column; align-items: stretch; }
}
</style>
