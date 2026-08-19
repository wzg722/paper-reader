<template>
  <div class="graph-page">
    <section class="stage">
      <canvas
        ref="canvasRef"
        class="graph-canvas"
        @mousedown="onDown"
        @mousemove="onMove"
        @mouseup="onUp"
        @mouseleave="onUp"
        @dblclick="onDblClick"
        @wheel.prevent="onWheel"
      />
      <div v-if="loading" class="stage-mask">正在生成知识图谱…</div>
      <div v-else-if="!nodes.length" class="stage-mask">
        文献库还没有可展示的论文，先去导入几篇，再点「重新布局」同步。
      </div>
      <div v-if="selected" class="detail-card">
        <div class="detail-kicker">{{ typeLabel(selected) }}<span v-if="selected.year"> · {{ selected.year }}</span></div>
        <div class="detail-title">{{ selected.label }}</div>
        <p v-if="selected.description" class="detail-desc">{{ selected.description }}</p>
        <div class="detail-actions">
          <el-button v-if="nodeCanRead(selected)" type="primary" size="small" @click="readNode(selected)">阅读</el-button>
          <el-button v-else-if="isPaperLike(selected)" type="primary" size="small" :loading="lookupLoading" @click="importNode(selected)">加入文献库</el-button>
        </div>
      </div>
      <div class="hint">拖拽节点 · 滚轮缩放 · 点击查看详情 · 双击进入阅读</div>
      <div class="legend">
        <span><i class="dot read"></i>已读论文</span>
        <span><i class="dot related"></i>相关论文</span>
        <span><i class="dot concept"></i>概念</span>
      </div>
    </section>

    <aside class="panel">
      <div class="block">
        <div class="block-title">
          <span class="ico search">🔍</span>
          按知识点找论文
        </div>
        <div class="search-row">
          <el-input
            v-model="q"
            placeholder="输入知识点，如：注意力机制 / OCR / Transformer..."
            @keyup.enter="search"
          />
          <el-button type="primary" :loading="searching" @click="search">搜索</el-button>
        </div>
        <div class="hot">
          <span class="muted">热门：</span>
          <button v-for="w in hotWords" :key="w" type="button" class="hot-tag" @click="searchWord(w)">{{ w }}</button>
        </div>
      </div>

      <div class="block">
        <div class="block-title">从中心论文探索</div>
        <el-select v-model="centerId" placeholder="选择一篇已读论文" style="width:100%" @change="onCenterChange">
          <el-option
            v-for="p in centerPapers"
            :key="p.id"
            :label="p.label"
            :value="p.id"
          />
        </el-select>
      </div>

      <div class="block">
        <div class="block-title">节点过滤</div>
        <div class="filters">
          <button type="button" class="chip" :class="{on: filters.paper}" @click="toggleFilter('paper')">论文</button>
          <button type="button" class="chip" :class="{on: filters.concept}" @click="toggleFilter('concept')">概念</button>
          <button type="button" class="chip" :class="{on: filters.unread}" @click="toggleFilter('unread')">未读</button>
        </div>
        <el-button class="relayout" @click="relayout" :loading="syncing">↻ 重新布局</el-button>
      </div>

      <div class="rec-block">
        <div class="block-title">
          相关推荐
          <span class="rec-src">arXiv{{ recTopic ? ' · ' + recTopic : '' }}</span>
        </div>
        <div v-if="!selected && !recQuery" class="rec-empty">点击左侧节点，将从 arXiv 推荐相关论文</div>
        <div v-else-if="recLoading && !recList.length" class="rec-empty">正在从 arXiv 检索…</div>
        <div v-else-if="!recList.length" class="rec-empty">暂无相关论文，换个节点或关键词试试</div>
        <div v-else class="rec-list">
          <article v-for="p in recList" :key="p.arxiv_id || p.title" class="rec-item">
            <div class="rec-title" @click="openRec(p)">{{ p.title }}</div>
            <div class="rec-meta">{{ p.year || '—' }} · {{ p.arxiv_id }}</div>
            <div class="rec-authors">{{ p.authors }}</div>
            <div class="rec-foot">
              <el-button v-if="p.in_library || p.paper_id" size="small" type="primary" @click="goReadRec(p)">阅读</el-button>
              <el-button v-else size="small" type="primary" :loading="importingId===hitKey(p)" @click="openImport(p)">导入</el-button>
            </div>
          </article>
        </div>
        <el-pagination
          v-if="recTotal > 0"
          class="rec-pager"
          small
          layout="total, prev, pager, next"
          :total="recTotal"
          v-model:current-page="recPage"
          v-model:page-size="recSize"
          :pager-count="5"
          @current-change="loadRecs"
        />
      </div>

      <div class="suggest">
        <div class="block-title">
          <span class="ico bulb">💡</span>
          探索路径建议
        </div>
        <p>{{ pathHint }}</p>
      </div>
    </aside>

    <el-dialog v-model="importVisible" title="加入文献库" width="560px" destroy-on-close>
      <div class="import-preview">
        <div v-if="lookupLoading" class="muted">正在从 arXiv 查找对应论文…</div>
        <template v-else-if="pending">
          <div class="import-title">{{ pending.title }}</div>
          <div class="muted">
            {{ pending.authors || '—' }} · {{ pending.year || '—' }}
            <span v-if="pending.arxiv_id"> · {{ pending.arxiv_id }}</span>
          </div>
        </template>
      </div>
      <el-form label-width="90px" style="margin-top:16px">
        <el-form-item label="类别">
          <el-select v-model="importForm.category" clearable placeholder="请选择文件夹" style="width:100%">
            <el-option v-for="c in folderOptions" :key="c.id" :label="c.label" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="importForm.status" style="width:100%">
            <el-option label="想读" value="想读" />
            <el-option label="在读" value="在读" />
            <el-option label="读完" value="读完" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="importForm.tags" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="importForm.intro" type="textarea" :rows="2" />
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
        <el-button type="primary" :loading="!!importingId" :disabled="lookupLoading || !pending?.title || (pending._nodeId && !pending.arxiv_id)" @click="confirmImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import api from '@/api/http'
import { useNotifyStore } from '@/stores/notify'

const router = useRouter()
const canvasRef = ref(null)
const nodes = ref([])
const edges = ref([])
const selected = ref(null)
const q = ref('')
const searching = ref(false)
const syncing = ref(false)
const loading = ref(true)
const lookupLoading = ref(false)
const centerId = ref(null)
const matchIds = ref(new Set())
const filters = reactive({ paper: true, concept: true, unread: true })
const hotWords = ['注意力机制', 'OCR', 'Transformer', '目标检测', '预训练']
const recList = ref([])
const recTotal = ref(0)
const recPage = ref(1)
const recSize = ref(5)
const recLoading = ref(false)
const recTopic = ref('')
const recQuery = ref('')
const notifyStore = useNotifyStore()
const categories = ref([])
const importingId = ref('')
const importVisible = ref(false)
const pending = ref(null)
const importForm = reactive({ category: null, status: '想读', tags: '', intro: '', parse_mode: 'ocr' })
let recSeq = 0

const view = { scale: 1, x: 0, y: 0 }
const drag = { mode: '', id: null, ox: 0, oy: 0, moved: false }
const positions = {}
const vel = {}
let raf = 0
let dpr = 1
let cssW = 900
let cssH = 560
let ro = null

const folderOptions = computed(() => {
  const list = categories.value || []
  const byId = new Map(list.map((c) => [c.id, c]))
  return list.map((c) => {
    const parts = [c.name]
    const seen = new Set([c.id])
    let p = c.parent ? byId.get(c.parent) : null
    while (p && !seen.has(p.id)) {
      parts.unshift(p.name)
      seen.add(p.id)
      p = p.parent ? byId.get(p.parent) : null
    }
    return { id: c.id, label: parts.join(' / ') }
  })
})

const centerPapers = computed(() =>
  nodes.value.filter((n) => n.node_type === 'paper' && n.has_pdf),
)

watch(() => selected.value?.id, () => {
  recPage.value = 1
  recQuery.value = ''
  loadRecs()
})

const visibleIds = computed(() => {
  const ids = new Set()
  for (const n of nodes.value) {
    const kind = visualKind(n)
    if (kind === 'concept' && !filters.concept) continue
    if (kind === 'read' && !filters.paper) continue
    if (kind === 'related' && !filters.unread) continue
    ids.add(n.id)
  }
  return ids
})

const pathHint = computed(() => {
  const center = nodes.value.find((n) => n.id === centerId.value) || selected.value
  if (!center || visualKind(center) === 'concept') {
    return '选择一篇中心论文后，将沿相连概念展开，帮你发现尚未阅读的相关工作。'
  }
  const neighborIds = new Set()
  for (const e of edges.value) {
    if (e.source_node === center.id) neighborIds.add(e.target_node)
    if (e.target_node === center.id) neighborIds.add(e.source_node)
  }
  const concepts = nodes.value.filter((n) => neighborIds.has(n.id) && n.node_type === 'concept').map((n) => n.short_label || n.label)
  const unread = nodes.value.filter((n) => visualKind(n) === 'related' && (neighborIds.has(n.id) || sharesConcept(center, n))).map((n) => n.short_label || n.label)
  const cname = center.short_label || center.label
  const cpart = concepts.slice(0, 2).join(' / ') || '相关概念'
  const upart = unread.slice(0, 2).join(' / ') || '相关工作'
  return `从「${cname}」出发 → 沿「${cpart}」概念展开 → 发现 ${upart} 等未读工作 → 加入文献库精读。`
})

function visualKind(n) {
  if (!n) return 'related'
  if (n.node_type === 'concept') return 'concept'
  if (n.has_pdf) return 'read'
  return 'related'
}

function isPaperLike(n) {
  return n && n.node_type !== 'concept'
}

function nodeCanRead(n) {
  return !!(n && n.has_pdf)
}

function typeLabel(n) {
  const k = visualKind(n)
  if (k === 'concept') return '概念'
  if (k === 'read') return '已读论文'
  return '相关论文'
}

function sharesConcept(a, b) {
  const aC = new Set()
  const bC = new Set()
  for (const e of edges.value) {
    const otherA = e.source_node === a.id ? e.target_node : e.target_node === a.id ? e.source_node : null
    const otherB = e.source_node === b.id ? e.target_node : e.target_node === b.id ? e.source_node : null
    const na = nodes.value.find((x) => x.id === otherA)
    const nb = nodes.value.find((x) => x.id === otherB)
    if (na?.node_type === 'concept') aC.add(na.id)
    if (nb?.node_type === 'concept') bC.add(nb.id)
  }
  for (const id of aC) if (bC.has(id)) return true
  return false
}

function nodeRadius(n) {
  if (visualKind(n) === 'concept') return 16
  const cites = Number(n.cites) || 0
  return 12 + Math.min(10, Math.log10(cites + 10) * 3)
}

async function load(opts = {}) {
  const { doSync = false } = opts
  loading.value = !nodes.value.length
  try {
    if (doSync) {
      syncing.value = true
      await api.post('/graph/sync/')
    }
    const data = await api.get('/graph/data/')
    nodes.value = data.nodes || []
    edges.value = data.edges || []
    if (!centerId.value && centerPapers.value[0]) {
      const ppocr = centerPapers.value.find((p) => /pp-?ocr/i.test(p.label))
      centerId.value = (ppocr || centerPapers.value[0]).id
    }
    if (centerId.value && (!selected.value || !nodes.value.some((n) => n.id === selected.value.id))) {
      selected.value = nodes.value.find((n) => n.id === centerId.value) || selected.value
    }
    initPositions(opts.reset)
    fitView()
    draw()
  } catch (e) {
    ElMessage.error(e.message || '图谱加载失败')
  } finally {
    loading.value = false
    syncing.value = false
  }
}

function initPositions(reset = false) {
  const cx = cssW / 2
  const cy = cssH / 2
  if (reset) {
    for (const k of Object.keys(positions)) delete positions[k]
  }
  const list = nodes.value
  list.forEach((n, i) => {
    if (positions[n.id] && !reset) return
    const a = (i / Math.max(list.length, 1)) * Math.PI * 2
    const ring = visualKind(n) === 'concept' ? 90 : 180
    const jitter = (n.id % 17) - 8
    positions[n.id] = {
      x: cx + Math.cos(a) * (ring + jitter * 6),
      y: cy + Math.sin(a) * (ring + jitter * 4),
    }
    vel[n.id] = { x: 0, y: 0 }
  })
}

function fitView() {
  view.scale = 1
  view.x = 0
  view.y = 0
}

function resize() {
  const canvas = canvasRef.value
  if (!canvas) return
  const parent = canvas.parentElement
  cssW = parent.clientWidth || 900
  cssH = parent.clientHeight || 560
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(cssW * dpr)
  canvas.height = Math.round(cssH * dpr)
  canvas.style.width = `${cssW}px`
  canvas.style.height = `${cssH}px`
  draw()
}

function worldFromEvent(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  return { mx, my, x: (mx - view.x) / view.scale, y: (my - view.y) / view.scale }
}

function hitTest(wx, wy) {
  let best = null
  let bestD = 1e9
  for (const n of nodes.value) {
    if (!visibleIds.value.has(n.id)) continue
    const p = positions[n.id]
    if (!p) continue
    const d = Math.hypot(p.x - wx, p.y - wy)
    const r = nodeRadius(n) + 6
    if (d < r && d < bestD) {
      best = n
      bestD = d
    }
  }
  return best
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, cssW, cssH)
  const g = ctx.createLinearGradient(0, 0, cssW, cssH)
  g.addColorStop(0, '#08111f')
  g.addColorStop(1, '#0d1b33')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, cssW, cssH)

  ctx.save()
  ctx.translate(view.x, view.y)
  ctx.scale(view.scale, view.scale)

  const vis = visibleIds.value
  const matched = matchIds.value
  ctx.lineWidth = 1.2
  for (const e of edges.value) {
    if (!vis.has(e.source_node) || !vis.has(e.target_node)) continue
    const a = positions[e.source_node]
    const b = positions[e.target_node]
    if (!a || !b) continue
    ctx.strokeStyle = 'rgba(148,163,184,.32)'
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.lineTo(b.x, b.y)
    ctx.stroke()
  }

  for (const n of nodes.value) {
    if (!vis.has(n.id)) continue
    const p = positions[n.id]
    if (!p) continue
    const kind = visualKind(n)
    const r = nodeRadius(n)
    const dim = matched.size && !matched.has(n.id)
    const color = kind === 'concept' ? '#8b5cf6' : kind === 'read' ? '#3b82f6' : '#94a3b8'
    ctx.globalAlpha = dim ? 0.22 : 1
    ctx.shadowColor = color
    ctx.shadowBlur = selected.value?.id === n.id ? 18 : 10
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2)
    ctx.fill()
    if (selected.value?.id === n.id) {
      ctx.shadowBlur = 0
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.stroke()
    }
    ctx.shadowBlur = 0
    ctx.fillStyle = '#e2e8f0'
    ctx.font = `${kind === 'concept' ? 12 : 13}px "Microsoft YaHei", "Segoe UI", sans-serif`
    ctx.textBaseline = 'middle'
    const label = n.short_label || n.label || ''
    ctx.fillText(label, p.x + r + 8, p.y)
    ctx.globalAlpha = 1
  }
  ctx.restore()
}

function tick() {
  const vis = visibleIds.value
  const list = nodes.value.filter((n) => vis.has(n.id) && positions[n.id])
  const n = list.length
  if (n && drag.mode !== 'node') {
    const cx = cssW / 2 / view.scale - view.x / view.scale
    const cy = cssH / 2 / view.scale - view.y / view.scale
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = positions[list[i].id]
        const b = positions[list[j].id]
        let dx = a.x - b.x
        let dy = a.y - b.y
        let d2 = dx * dx + dy * dy || 1
        const d = Math.sqrt(d2)
        const force = Math.min(8, 2200 / d2)
        const fx = (dx / d) * force
        const fy = (dy / d) * force
        const va = vel[list[i].id] || (vel[list[i].id] = { x: 0, y: 0 })
        const vb = vel[list[j].id] || (vel[list[j].id] = { x: 0, y: 0 })
        va.x += fx
        va.y += fy
        vb.x -= fx
        vb.y -= fy
      }
    }
    for (const e of edges.value) {
      if (!vis.has(e.source_node) || !vis.has(e.target_node)) continue
      const a = positions[e.source_node]
      const b = positions[e.target_node]
      if (!a || !b) continue
      const dx = b.x - a.x
      const dy = b.y - a.y
      const d = Math.hypot(dx, dy) || 1
      const rest = 150
      const f = (d - rest) * 0.008
      const va = vel[e.source_node] || (vel[e.source_node] = { x: 0, y: 0 })
      const vb = vel[e.target_node] || (vel[e.target_node] = { x: 0, y: 0 })
      va.x += (dx / d) * f
      va.y += (dy / d) * f
      vb.x -= (dx / d) * f
      vb.y -= (dy / d) * f
    }
    for (const node of list) {
      if (drag.mode === 'node' && drag.id === node.id) continue
      const p = positions[node.id]
      const v = vel[node.id] || (vel[node.id] = { x: 0, y: 0 })
      v.x += (cx - p.x) * 0.002
      v.y += (cy - p.y) * 0.002
      v.x *= 0.82
      v.y *= 0.82
      p.x += v.x
      p.y += v.y
    }
  }
  draw()
  raf = requestAnimationFrame(tick)
}

function onDown(e) {
  const { mx, my, x, y } = worldFromEvent(e)
  const n = hitTest(x, y)
  drag.moved = false
  drag.ox = mx
  drag.oy = my
  if (n) {
    selected.value = n
    drag.mode = 'node'
    drag.id = n.id
  } else {
    drag.mode = 'pan'
    drag.id = null
  }
  draw()
}

function onMove(e) {
  if (!drag.mode) return
  const { mx, my } = worldFromEvent(e)
  const dx = mx - drag.ox
  const dy = my - drag.oy
  if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true
  if (drag.mode === 'node') {
    const p = positions[drag.id]
    if (p) {
      p.x += dx / view.scale
      p.y += dy / view.scale
    }
  } else {
    view.x += dx
    view.y += dy
  }
  drag.ox = mx
  drag.oy = my
  draw()
}

function onUp() {
  drag.mode = ''
  drag.id = null
}

function onDblClick(e) {
  const { x, y } = worldFromEvent(e)
  const n = hitTest(x, y)
  if (!n) return
  if (n.paper) readNode(n)
  else if (isPaperLike(n)) importNode(n)
}

function onWheel(e) {
  const { mx, my } = worldFromEvent(e)
  const factor = e.deltaY > 0 ? 0.9 : 1.1
  const next = Math.min(2.6, Math.max(0.35, view.scale * factor))
  const wx = (mx - view.x) / view.scale
  const wy = (my - view.y) / view.scale
  view.scale = next
  view.x = mx - wx * view.scale
  view.y = my - wy * view.scale
  draw()
}

function toggleFilter(key) {
  filters[key] = !filters[key]
  draw()
}

async function search() {
  const kw = q.value.trim()
  if (!kw) {
    matchIds.value = new Set()
    draw()
    return
  }
  searching.value = true
  try {
    const data = await api.get('/graph/search/', { params: { q: kw } })
    const ids = new Set()
    for (const n of [...(data.concepts || []), ...(data.papers || [])]) ids.add(n.id)
    for (const n of nodes.value) {
      const blob = `${n.label} ${n.tags || ''} ${n.description || ''}`.toLowerCase()
      if (blob.includes(kw.toLowerCase())) ids.add(n.id)
    }
    matchIds.value = ids
    const first = nodes.value.find((n) => ids.has(n.id) && visibleIds.value.has(n.id))
    if (first) {
      selected.value = first
      const p = positions[first.id]
      if (p) {
        view.x = cssW / 2 - p.x * view.scale
        view.y = cssH / 2 - p.y * view.scale
      }
    } else {
      recQuery.value = kw
      recPage.value = 1
      loadRecs()
      ElMessage.info('图谱中没有匹配节点，已改为从 arXiv 按关键词推荐')
    }
    draw()
  } catch (e) {
    ElMessage.error(e.message || '搜索失败')
  } finally {
    searching.value = false
  }
}

function searchWord(w) {
  q.value = w
  search()
}

function onCenterChange() {
  const n = nodes.value.find((x) => x.id === centerId.value)
  if (!n) return
  selected.value = n
  const p = positions[n.id]
  if (p) {
    view.x = cssW / 2 - p.x * view.scale
    view.y = cssH / 2 - p.y * view.scale
  }
  draw()
}

async function relayout() {
  await load({ doSync: true, reset: true })
}

function hitKey(p) {
  return p?.arxiv_id || p?.doi || p?.title || ''
}

async function loadRecs() {
  const node = selected.value
  const kw = recQuery.value.trim() || q.value.trim()
  if (!node && !kw) {
    recList.value = []
    recTotal.value = 0
    recTopic.value = ''
    return
  }
  const seq = ++recSeq
  recLoading.value = true
  try {
    const data = await api.get('/graph/recommend/', {
      params: {
        node_id: kw && recQuery.value ? undefined : node?.id,
        q: recQuery.value || (!node ? kw : undefined),
        page: recPage.value,
        page_size: recSize.value,
      },
    })
    if (seq !== recSeq) return
    recList.value = data.results || []
    recTotal.value = data.count || 0
    recTopic.value = data.topic || data.node_label || ''
  } catch (e) {
    if (seq !== recSeq) return
    recList.value = []
    recTotal.value = 0
    ElMessage.error(e.message || 'arXiv 推荐失败')
  } finally {
    if (seq === recSeq) recLoading.value = false
  }
}

function openRec(p) {
  if (p.abs_url) window.open(p.abs_url, '_blank')
  else if (p.arxiv_id) window.open(`https://arxiv.org/abs/${p.arxiv_id}`, '_blank')
}

function goReadRec(p) {
  const id = p.paper_id || p.id
  if (!id) return openImport(p)
  router.push({ name: 'library', query: { tab: 'reader', p: id } })
}

function resetImportForm(extra = {}) {
  importForm.category = extra.category ?? null
  importForm.status = extra.status || '想读'
  importForm.tags = extra.tags || ''
  importForm.intro = extra.intro || ''
  importForm.parse_mode = extra.parse_mode || 'ocr'
}

async function ensureCategories() {
  if (categories.value.length) return
  try { categories.value = await api.get('/papers/categories/') || [] } catch { categories.value = [] }
}

async function openImport(p) {
  await ensureCategories()
  pending.value = p
  resetImportForm({
    tags: recTopic.value || '',
    intro: (p.intro || p.abstract || '').slice(0, 400),
  })
  lookupLoading.value = false
  importVisible.value = true
}

function markNodeImported(nodeId, paperId, hasPdf = false) {
  const n = nodes.value.find((x) => x.id === nodeId)
  if (!n) return
  n.paper = paperId
  n.paper_id = paperId
  n.in_library = true
  n.has_pdf = !!hasPdf
  n.read_status = !!hasPdf
  n.node_type = 'paper'
  if (selected.value?.id === n.id) selected.value = { ...n }
}

async function confirmImport() {
  const p = pending.value
  if (!p?.title && !p?.arxiv_id) return
  if (lookupLoading.value) return ElMessage.warning('正在查找论文，请稍候')
  importingId.value = hitKey(p) || String(p._nodeId || 'import')
  const payload = {
    arxiv_id: p.arxiv_id || '',
    pdf_url: p.pdf_url,
    title: p.title,
    authors: p.authors,
    year: p.year,
    doi: p.doi,
    abstract: p.abstract,
    venue: p.venue || 'arXiv',
    cites: p.cites || 0,
    download_pdf: 1,
    background: 1,
    category: importForm.category,
    status: importForm.status,
    tags: importForm.tags,
    intro: importForm.intro,
    parse_mode: importForm.parse_mode,
  }
  try {
    const data = p._nodeId
      ? await api.post(`/graph/nodes/${p._nodeId}/import_paper/`, payload)
      : await api.post('/papers/import-hit/', payload)
    p.in_library = true
    p.paper_id = data.id
    if (p._nodeId) markNodeImported(p._nodeId, data.id, !data.queued && !!data.has_local_pdf)
    importVisible.value = false
    const title = (data.title || p.title || '论文').slice(0, 60)
    if (data.already && !data.queued) {
      ElNotification({ type: 'info', title: '已在文献库', message: `《${title}》无需重复导入` })
    } else if (data.queued && data.job_id) {
      ElNotification({
        type: 'info',
        title: '已开始后台导入',
        message: `《${title}》正在下载解析，完成后会在右上角通知你`,
      })
      notifyStore.watchJob(data.job_id, title, data.id)
    } else {
      ElNotification({ type: 'success', title: '导入成功', message: `《${title}》已加入文献库` })
    }
  } catch (e) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    importingId.value = ''
  }
}

function readNode(n) {
  const id = n.paper || n.paper_id
  if (!id) return
  router.push({ name: 'library', query: { tab: 'reader', p: id } })
}

async function importNode(n) {
  if (!n?.id) return
  if (nodeCanRead(n)) return readNode(n)
  await ensureCategories()
  pending.value = {
    title: n.label,
    authors: '',
    year: n.year,
    arxiv_id: '',
    abstract: n.description,
    _nodeId: n.id,
  }
  resetImportForm({
    tags: n.tags || recTopic.value || '',
    intro: (n.description || '').slice(0, 400),
  })
  importVisible.value = true
  lookupLoading.value = true
  try {
    const data = await api.get(`/graph/nodes/${n.id}/lookup/`)
    if (data.has_pdf && data.paper_id) {
      markNodeImported(n.id, data.paper_id, true)
      importVisible.value = false
      ElMessage.success('本地已有 PDF，可直接阅读')
      return
    }
    const hit = data.hit
    if (!hit) {
      ElMessage.error('未在 arXiv 找到对应论文')
      return
    }
    pending.value = { ...hit, _nodeId: n.id }
    if (!importForm.intro) importForm.intro = (hit.abstract || hit.intro || '').slice(0, 400)
  } catch (e) {
    ElMessage.error(e.message || 'arXiv 查找失败')
  } finally {
    lookupLoading.value = false
  }
}

onMounted(async () => {
  await nextTick()
  resize()
  ro = new ResizeObserver(resize)
  if (canvasRef.value?.parentElement) ro.observe(canvasRef.value.parentElement)
  try { categories.value = await api.get('/papers/categories/') || [] } catch { categories.value = [] }
  await load({ doSync: true })
  raf = requestAnimationFrame(tick)
})

onUnmounted(() => {
  if (raf) cancelAnimationFrame(raf)
  ro?.disconnect()
})
</script>

<style scoped>
.graph-page {
  height: 100%;
  min-height: 0;
  display: flex;
  overflow: hidden;
  background: #fff;
}
.stage {
  flex: 1;
  min-width: 0;
  position: relative;
  background: #08111f;
}
.graph-canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
}
.stage-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 14px;
  pointer-events: none;
  padding: 24px;
  text-align: center;
}
.hint {
  position: absolute;
  left: 16px;
  bottom: 14px;
  color: rgba(255,255,255,.78);
  font-size: 12px;
  letter-spacing: .02em;
  pointer-events: none;
}
.legend {
  position: absolute;
  right: 16px;
  bottom: 14px;
  display: flex;
  gap: 14px;
  color: rgba(255,255,255,.82);
  font-size: 12px;
  pointer-events: none;
}
.legend span { display: flex; align-items: center; gap: 6px; }
.dot {
  width: 9px; height: 9px; border-radius: 50%; display: inline-block;
}
.dot.read { background: #3b82f6; }
.dot.related { background: #94a3b8; }
.dot.concept { background: #8b5cf6; }
.detail-card {
  position: absolute;
  left: 16px;
  bottom: 44px;
  width: min(360px, calc(100% - 32px));
  background: rgba(15, 23, 42, .88);
  border: 1px solid rgba(148,163,184,.25);
  color: #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  backdrop-filter: blur(8px);
}
.detail-kicker { font-size: 12px; color: #93c5fd; margin-bottom: 4px; }
.detail-title { font-weight: 700; font-size: 15px; line-height: 1.4; }
.detail-desc { margin: 6px 0 0; font-size: 12.5px; color: #cbd5e1; line-height: 1.5; }
.detail-actions { margin-top: 10px; }

.panel {
  width: 380px;
  flex: none;
  background: #fff;
  border-left: 1px solid var(--border);
  padding: 16px 16px 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}
.block-title {
  font-weight: 700;
  font-size: 15px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ico {
  width: 28px; height: 28px; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 14px;
}
.ico.search { background: #2563eb; color: #fff; }
.ico.bulb { background: #2563eb; color: #fff; border-radius: 50%; width: 26px; height: 26px; }
.search-row { display: flex; gap: 8px; }
.search-row :deep(.el-input) { flex: 1; }
.hot { margin-top: 10px; font-size: 13px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.hot-tag {
  border: 0; background: none; color: var(--primary); cursor: pointer; padding: 0;
  font-size: 13px;
}
.hot-tag:hover { text-decoration: underline; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #2563eb;
  border-radius: 999px;
  padding: 6px 14px;
  cursor: pointer;
  font-weight: 600;
}
.chip.on { background: #2563eb; color: #fff; border-color: #2563eb; }
.chip:not(.on) { background: #fff; color: var(--text-2); border-color: var(--border); }
.relayout {
  width: 100%;
  margin-top: 12px;
}
.rec-block {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}
.rec-src {
  margin-left: auto;
  font-weight: 500;
  font-size: 12px;
  color: var(--text-3);
}
.rec-empty {
  color: var(--text-3);
  font-size: 13px;
  padding: 16px 4px;
  text-align: center;
}
.rec-list { flex: 1; min-height: 0; overflow-y: auto; }
.rec-item {
  padding: 10px 4px 10px 0;
  border-bottom: 1px solid var(--border);
}
.rec-title {
  font-weight: 650;
  font-size: 13.5px;
  line-height: 1.4;
  cursor: pointer;
}
.rec-title:hover { color: var(--primary); }
.rec-meta, .rec-authors {
  color: var(--text-3);
  font-size: 12px;
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rec-foot { margin-top: 8px; display: flex; justify-content: flex-end; }
.rec-pager { margin-top: 8px; justify-content: center; }
.import-preview {
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 10px;
}
.import-title { font-weight: 650; font-size: 15px; line-height: 1.45; margin-bottom: 4px; }
.suggest {
  flex: none;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
}
.suggest p { margin: 0; color: var(--text-2); font-size: 13px; line-height: 1.65; }
@media (max-width: 960px) {
  .graph-page { flex-direction: column; }
  .panel { width: 100%; height: 48%; }
}
</style>
