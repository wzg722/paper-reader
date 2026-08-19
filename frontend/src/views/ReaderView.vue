<template>
  <div class="reader" v-loading="loading">
    <div class="toolbar card">
      <el-select v-model="paperId" placeholder="选择论文" filterable style="width:240px" @change="loadPaper">
        <el-option v-for="p in paperList" :key="p.id" :label="p.title" :value="p.id" />
      </el-select>
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button value="layout">📄 PDF原版</el-radio-button>
        <el-radio-button value="layout-bi">🗂 双语版面对照</el-radio-button>
      </el-radio-group>
      <el-button size="small" type="primary" @click="runPipeline" :loading="pipelineBusy">①解析→②翻译→③对照</el-button>
      <el-button size="small" @click="translateAll" :loading="translating">AI对齐翻译</el-button>
      <el-button size="small" @click="genSummary" :loading="summarizing">AI精读总结</el-button>
      <el-button v-if="paper?.has_pdf" size="small" :loading="reparsing" @click="reparseLayout">♻ PaddleOCR还原版面</el-button>
      <el-button size="small" :type="ocrMode ? 'primary' : ''" @click="toggleOcrMode">{{ ocrMode ? '退出截图' : '📷 截图OCR' }}</el-button>
      <span class="muted">进度 {{ progress }}%</span>
      <span v-if="pipelineTip" class="pipe-tip">{{ pipelineTip }}</span>
    </div>

    <div class="body" :class="bodyClass">
      <div class="page-dock" :class="{ collapsed: pagesCollapsed }">
        <aside v-show="!pagesCollapsed" class="page-panel card">
          <div class="left-tabs">
            <button type="button" :class="{ active: leftTab==='pages' }" @click="leftTab='pages'">页码</button>
            <button type="button" :class="{ active: leftTab==='toc' }" @click="leftTab='toc'">大纲</button>
          </div>
          <div v-if="leftTab==='pages'">
            <div class="page-panel-title">{{ currentPage }} / {{ pageTotal }}</div>
            <div
              v-for="t in pageThumbs"
              :key="t.page"
              class="thumb"
              :class="{ active: t.page === currentPage }"
              @click="jumpPage(t.page)"
            >
              <img v-if="t.url" :src="t.url" :alt="'p'+t.page" />
              <span>{{ t.page }}</span>
            </div>
          </div>
          <div v-else class="toc-list">
            <div v-if="!tocItems.length" class="toc-empty">暂无一级/二级标题，可重新解析论文</div>
            <div
              v-for="o in tocItems"
              :key="o.id"
              class="ol-item"
              :class="{ active: activeSection===o.id, h2: o.level===2 }"
              @click="jumpSection(o)"
            >{{ o.title }}</div>
          </div>
        </aside>
        <button
          class="page-handle"
          type="button"
          :title="pagesCollapsed ? '展开左侧栏' : '收起左侧栏'"
          @click="pagesCollapsed = !pagesCollapsed"
        >
          <span class="ai-handle-icon">{{ pagesCollapsed ? '›' : '‹' }}</span>
          <span v-if="pagesCollapsed" class="ai-handle-label">{{ leftTab==='toc' ? '大纲' : '页码' }}</span>
        </button>
      </div>

      <section v-if="viewMode==='layout'" class="content card pdf-pane">
        <PdfViewer
          v-if="paper?.has_pdf && paper?.pdf_file_url"
          ref="pdfSoloRef"
          :file-url="paper.pdf_file_url"
          :paper-id="paper.id"
          :layout-meta="paper.layout_meta"
          :show-thumbs="false"
          @page-change="onPdfPage"
        />
        <div v-else class="empty muted">
          <p>暂无 PDF 原文件。</p>
          <el-button type="primary" :loading="fetchingPdf" @click="fetchPdf">⬇ 下载 PDF</el-button>
        </div>
      </section>

      <section v-else class="content card pdf-pane">
        <LayoutBilingual
          v-if="paper?.has_pdf && paper?.pdf_file_url"
          ref="layoutBiRef"
          :file-url="paper.pdf_file_url"
          :paper-id="paper.id"
          :layout-meta="paper.layout_meta"
          :paras="paras"
          :translating="translating"
          @page-change="onPdfPage"
          @translate-page="translatePage"
          @preview="previewImg"
          @context="onLayoutContext"
          @pick="onPaperPick"
          @active-change="onActivePara"
        />
        <div v-else class="empty muted">
          <p>双语版面对照需要 PDF + 版面解析。</p>
          <el-button type="primary" :loading="fetchingPdf" @click="fetchPdf">⬇ 下载并解析</el-button>
        </div>
      </section>

      <div
        v-if="ocrMode"
        class="ocr-mask"
        :class="{ busy: ocrBusy }"
        @mousedown.prevent="onOcrDown"
      >
        <div class="ocr-hint">{{ ocrBusy ? '正在识别并翻译，请稍候…' : '在左侧原文 PDF 上拖拽框选 · Esc 取消' }}</div>
        <div v-if="ocrBox.show" class="ocr-rect" :style="ocrRectStyle" />
      </div>

      <div class="ai-dock" :class="{ collapsed: aiCollapsed }">
        <button
          class="ai-handle"
          type="button"
          :title="aiCollapsed ? '展开右侧栏' : '收起右侧栏'"
          @click="aiCollapsed = !aiCollapsed"
        >
          <span class="ai-handle-icon">{{ aiCollapsed ? '‹' : '›' }}</span>
          <span v-if="aiCollapsed" class="ai-handle-label">问 AI</span>
        </button>
        <aside v-show="!aiCollapsed" class="ai-panel card">
          <div class="ai-head">
            <div class="ai-head-title">问 AI</div>
            <div class="ai-head-sub">基于当前论文作答</div>
          </div>
          <div class="ai-tabs">
            <button type="button" :class="{ active: aiTab==='chat' }" @click="aiTab='chat'">问答</button>
            <button type="button" :class="{ active: aiTab==='sum' }" @click="aiTab='sum'">总结</button>
            <button type="button" :class="{ active: aiTab==='notes' }" @click="aiTab='notes'">
              笔记 <span v-if="notes.length" class="tab-n">{{ notes.length }}</span>
            </button>
          </div>

          <div v-show="aiTab==='chat'" class="ai-chat">
            <div ref="chatRef" class="chat-msgs">
              <div v-if="!chat.length && !asking" class="chat-empty">
                <div class="chat-empty-icon">✦</div>
                <p>问问这篇论文想搞清楚的问题</p>
                <div class="chips">
                  <button v-for="c in askChips" :key="c" type="button" class="chip" @click="quickAsk(c)">{{ c }}</button>
                </div>
              </div>
              <div v-for="(m, i) in chat" :key="i" class="msg" :class="m.role">
                <div class="msg-who">{{ m.role === 'user' ? '我' : 'AI' }}</div>
                <div class="msg-bubble" v-html="formatMsg(m.content)"></div>
              </div>
              <div v-if="asking" class="msg assistant">
                <div class="msg-who">AI</div>
                <div class="msg-bubble typing"><span></span><span></span><span></span></div>
              </div>
            </div>
            <div class="composer">
              <el-input
                v-model="question"
                type="textarea"
                :rows="2"
                resize="none"
                placeholder="输入问题，Enter 发送"
                @keydown.enter.exact.prevent="ask"
              />
              <el-button type="primary" :loading="asking" :disabled="!question.trim()" @click="ask">发送</el-button>
            </div>
          </div>

          <div v-show="aiTab==='sum'" class="ai-extra">
            <div v-if="summaryView" class="sum-card">
              <div v-for="s in summaryView.sections" :key="s.key" class="sum-sec">
                <h5>{{ s.title }}</h5>
                <ul v-if="s.items?.length" class="sum-list">
                  <li v-for="(it, i) in s.items" :key="i">
                    <p v-if="it.zh" class="sum-zh">{{ it.zh }}</p>
                    <p v-if="it.en" class="sum-en">{{ it.en }}</p>
                  </li>
                </ul>
                <template v-else>
                  <p v-if="s.zh" class="sum-zh">{{ s.zh }}</p>
                  <p v-if="s.en" class="sum-en">{{ s.en }}</p>
                </template>
              </div>
              <div v-if="summaryView.glossary.length" class="sum-sec">
                <h5>术语</h5>
                <div v-for="(g, i) in summaryView.glossary" :key="i" class="sum-term">
                  <span class="sum-term-en">{{ g.en }}</span>
                  <span class="sum-term-zh">{{ g.zh }}</span>
                  <p v-if="g.desc" class="sum-en">{{ g.desc }}</p>
                </div>
              </div>
              <p v-if="summaryView.needRegen" class="sum-hint">当前总结只有中文，点下方重新生成可得到中英对照。</p>
              <el-button size="small" :loading="summarizing" @click="genSummary">重新生成</el-button>
            </div>
            <div v-else class="chat-empty">
              <p>还没有精读总结</p>
              <el-button size="small" type="primary" :loading="summarizing" @click="genSummary">生成总结</el-button>
            </div>
          </div>

          <div v-show="aiTab==='notes'" class="ai-extra">
            <div v-if="!notes.length" class="chat-empty">暂无笔记，可在原文划词或截图后保存</div>
            <div v-for="n in notes" :key="n.id" class="note-card" @click="jumpNote(n)">
              <div class="note-main">{{ n.note_text || n.ai_summary || n.sel_text }}</div>
              <div v-if="n.sel_text && n.note_text" class="note-src">{{ n.sel_text }}</div>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <div
      v-if="bubble.show"
      ref="bubbleRef"
      class="bubble card"
      :class="{ dragging: bubble.dragging }"
      :style="{ left: bubble.x + 'px', top: bubble.y + 'px' }"
      @pointerdown="onBubblePointerDown"
      @pointermove="onBubblePointerMove"
      @pointerup="onBubblePointerUp"
      @pointercancel="onBubblePointerUp"
      @contextmenu.prevent="closeBubble"
    >
      <div class="bubble-head">
        <span class="bubble-drag">⋮⋮</span>
        划词笔记 · 拖动可移动 · 划选其他文字会同步更新 · 再右击关闭
      </div>
      <div class="bubble-lab">原文内容（可改）</div>
      <textarea v-model="bubble.text" rows="3" />
      <div class="bubble-lab">AI 翻译（可改）</div>
      <textarea v-model="bubble.translation" rows="3" :placeholder="bubble.loading ? '正在翻译…' : ''" />
      <div class="bubble-lab">AI 总结（可改）</div>
      <textarea v-model="bubble.summary" rows="2" :placeholder="bubble.loading ? '正在总结…' : ''" />
      <div class="bubble-lab">加入笔记（可改）</div>
      <textarea v-model="bubble.note" rows="2" placeholder="写自己的批注，可与翻译/总结一起保存" />
      <div class="bubble-actions">
        <el-select v-model="bubble.visibility" size="small" style="width:110px">
          <el-option label="🌍公开" value="public" />
          <el-option label="👥仅好友" value="friends" />
          <el-option label="🔒私密" value="private" />
        </el-select>
        <el-button size="small" @click="regenBubble" :loading="bubble.loading">重新生成</el-button>
        <el-button size="small" type="primary" @click="saveNote">存为笔记</el-button>
        <el-button size="small" @click="addHighlight('y')">高亮</el-button>
        <el-button size="small" @click="closeBubble">关闭</el-button>
      </div>
    </div>

    <el-dialog v-model="ocrDialog" title="📷 截图 OCR + AI 翻译总结" width="620px" append-to-body>
      <div class="ocr-meta">截图区域：<b>{{ ocrResult.rect || '—' }}</b></div>
      <div v-if="ocrResult.preview" class="ocr-preview">
        <img :src="ocrResult.preview" alt="截图预览" />
      </div>
      <el-form label-position="top">
        <el-form-item label="OCR 识别（可编辑）"><el-input v-model="ocrResult.ocr_text" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="AI 翻译（可编辑）"><el-input v-model="ocrResult.ai_translation" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="AI 总结（可编辑）"><el-input v-model="ocrResult.ai_summary" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="加入笔记（可编辑）"><el-input v-model="ocrResult.note" type="textarea" :rows="2" placeholder="可写自己的批注，与识别结果一起保存" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ocrDialog=false">关闭</el-button>
        <el-button type="primary" @click="saveOcrNote">存为笔记</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="imgPreview.show" width="80%" title="图片预览" append-to-body>
      <img :src="imgPreview.url" style="max-width:100%" />
    </el-dialog>

    <input ref="fileInput" type="file" accept="image/*" hidden @change="onOcrFile" />
  </div>
</template>


<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api/http'
import PdfViewer from '@/components/PdfViewer.vue'
import LayoutBilingual from '@/components/LayoutBilingual.vue'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  initialPaperId: { type: [Number, String], default: null },
})

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const paper = ref(null)
const paperList = ref([])
const paperId = ref(null)
const viewMode = ref('layout-bi')
const layoutBiRef = ref(null)
const pdfSoloRef = ref(null)
const progress = ref(0)
const activeSection = ref('')
const flashIndex = ref(-1)
const notes = ref([])
const chat = ref([])
const question = ref('')
const asking = ref(false)
const translating = ref(false)
const summarizing = ref(false)
const conversationId = ref(null)
const chatRef = ref(null)
const aiTab = ref('chat')
const askChips = ['核心贡献是什么？', '实验结论有哪些？', '有什么局限性？']
const ocrMode = ref(false)
const ocrDialog = ref(false)
const ocrBusy = ref(false)
const ocrBox = reactive({ show: false, x0: 0, y0: 0, x1: 0, y1: 0 })
const ocrResult = reactive({
  ocr_text: '', ai_translation: '', ai_summary: '', note: '',
  image_path: '', rect: '', preview: '',
})
const reparsing = ref(false)
const pipelineBusy = ref(false)
const pipelineTip = ref('')
const fileInput = ref(null)
const imgPreview = reactive({ show: false, url: '' })
const leftTab = ref(localStorage.getItem('pm_left_tab') || 'pages')
const bubbleRef = ref(null)
const bubble = reactive({
  show: false, x: 0, y: 0, text: '', translation: '', summary: '', note: '',
  para_index: 0, visibility: 'public', loading: false, dragging: false,
})
const bubbleDrag = { dx: 0, dy: 0 }
let bubbleAiToken = 0
let bubbleSelTimer = 0
let lastBubbleSel = ''
const fetchingPdf = ref(false)
const aiCollapsed = ref(localStorage.getItem('pm_ai_collapsed') === '1')
const pagesCollapsed = ref(localStorage.getItem('pm_pages_collapsed') === '1')
const currentPage = ref(1)

const pageTotal = computed(() => paper.value?.layout_meta?.page_count || (paper.value?.layout_meta?.pages || []).length || 1)
const pageThumbs = computed(() => {
  const pages = paper.value?.layout_meta?.pages || []
  if (pages.length) {
    return pages.map((p) => ({
      page: p.page,
      url: p.preview ? `/media/${p.preview}` : (p.thumb ? (String(p.thumb).startsWith('/media') ? p.thumb : `/media/${p.thumb}`) : ''),
    }))
  }
  return Array.from({ length: pageTotal.value }, (_, i) => ({ page: i + 1, url: '' }))
})

const ocrRectStyle = computed(() => {
  const x = Math.min(ocrBox.x0, ocrBox.x1)
  const y = Math.min(ocrBox.y0, ocrBox.y1)
  return {
    left: `${x}px`,
    top: `${y}px`,
    width: `${Math.abs(ocrBox.x1 - ocrBox.x0)}px`,
    height: `${Math.abs(ocrBox.y1 - ocrBox.y0)}px`,
  }
})

const paras = computed(() => paper.value?.content_json || [])

const SUM_SECTIONS = [
  { key: 'core', title: '核心' },
  { key: 'problem', title: '研究问题' },
  { key: 'method', title: '方法创新' },
  { key: 'result', title: '主要结果' },
  { key: 'limit', title: '结论与局限' },
  { key: 'insight', title: '领域启发' },
]

function asBi(val) {
  if (val == null || val === '') return { zh: '', en: '' }
  if (typeof val === 'string') return { zh: val, en: '' }
  if (Array.isArray(val)) {
    const items = val.map((x) => {
      if (typeof x === 'string') return { zh: x, en: '' }
      return asBi(x)
    }).filter((x) => x.zh || x.en)
    return {
      items,
      zh: items.map((x) => x.zh).filter(Boolean).join('\n'),
      en: items.map((x) => x.en).filter(Boolean).join('\n'),
    }
  }
  if (typeof val === 'object') {
    const zh = val.zh ?? val.zh_CN ?? val.chinese ?? ''
    const en = val.en ?? val.en_US ?? val.english ?? ''
    if (Array.isArray(zh) || Array.isArray(en)) {
      const zArr = Array.isArray(zh) ? zh : (zh ? [zh] : [])
      const eArr = Array.isArray(en) ? en : (en ? [en] : [])
      const n = Math.max(zArr.length, eArr.length)
      const items = Array.from({ length: n }, (_, i) => ({
        zh: String(zArr[i] || ''),
        en: String(eArr[i] || ''),
      })).filter((x) => x.zh || x.en)
      return {
        items,
        zh: items.map((x) => x.zh).filter(Boolean).join('\n'),
        en: items.map((x) => x.en).filter(Boolean).join('\n'),
      }
    }
    return { zh: String(zh || ''), en: String(en || '') }
  }
  return { zh: String(val), en: '' }
}

const summaryView = computed(() => {
  const sm = paper.value?.ai_summary
  if (!sm || typeof sm !== 'object') return null
  const sections = SUM_SECTIONS.map((s) => ({ ...s, ...asBi(sm[s.key]) }))
    .filter((s) => s.zh || s.en || s.items?.length)
  const glossary = (sm.glossary || []).filter((g) => g && (g.en || g.zh))
  if (!sections.length && !glossary.length) return null
  const needRegen = sections.some((s) => s.zh && !s.en) && !sections.some((s) => s.en)
  return { sections, glossary, needRegen }
})

function headingLevel(text) {
  const t = String(text || '').replace(/\s+/g, ' ').trim()
  if (t.length < 3 || t.length > 90) return 0
  if (/^\d+\.\d+(\.\d+)?(\s|$)/.test(t)) return 2
  if (/^(abstract|introduction|related work|related works|method|methods|methodology|approach|experiment|experiments|evaluation|result|results|discussion|conclusion|conclusions|reference|references|appendix|acknowledgements?|acknowledgment)\b/i.test(t) && t.length < 80) return 1
  if (/^\d+\.?\s+[A-Z\u4e00-\u9fff]/.test(t) && t.length < 80) return 1
  const words = t.split(/\s+/)
  if (t === t.toUpperCase() && /[A-Z]/.test(t) && words.length >= 1 && words.length <= 12) return 1
  return 0
}

const tocItems = computed(() => {
  const list = paras.value || []
  const fromPaper = (paper.value?.outline || []).filter((o) => {
    const t = String(o.title || '')
    if (/^Page\s+\d+$/i.test(t) || t === '全文' || t === '文档') return false
    return true
  })
  if (fromPaper.some((o) => o.level || headingLevel(o.title))) {
    return fromPaper.map((o, i) => ({
      ...o,
      id: o.id || `s${i}`,
      level: o.level || headingLevel(o.title) || 1,
    }))
  }
  const items = []
  list.forEach((p, i) => {
    const lv = headingLevel(p.en)
    if (!lv) return
    items.push({
      id: p.section_id || `h${i}`,
      title: String(p.en || '').trim().slice(0, 80),
      para_index: i,
      page: p.page,
      level: lv,
    })
  })
  return items
})

function hasLayoutBlocks(p) {
  const list = p?.content_json || []
  if (list.some(b => Array.isArray(b.bbox) && b.bbox.length >= 4 && b.page)) return true
  const mode = String(p?.layout_meta?.parse_mode || '')
  if (mode.includes('ocr') || mode === 'paddleocr' || mode === 'mineru') {
    return list.some(b => b.page && String(b.en || '').trim().length > 2)
  }
  return false
}

function pendingTextCount(p, page = null) {
  return (p?.content_json || []).filter(b => {
    if ((b.type || 'text') === 'figure') return false
    if (page != null && Number(b.page || 0) !== Number(page)) return false
    const zh = String(b.zh || '').trim()
    const en = String(b.en || '').trim()
    if (!en || en.startsWith('[')) return false
    return !zh || zh.startsWith('（待') || zh.includes('离线占位') || zh.includes('【译文占位】')
  }).length
}

function mediaUrl(para) {
  if (para.image_url) return para.image_url
  if (para.image) return para.image.startsWith('/media') ? para.image : `/media/${para.image}`
  return ''
}
function previewImg(url) {
  imgPreview.url = url
  imgPreview.show = true
}
function onPdfPage(p) {
  currentPage.value = p
  progress.value = Math.min(100, Math.round((p / Math.max(paper.value?.layout_meta?.page_count || 1, 1)) * 100))
  if (viewMode.value === 'layout-bi' && !translating.value && !pipelineBusy.value) {
    if (pendingTextCount(paper.value, p) > 0) {
      translatePage(p)
    }
  }
}

function jumpPage(p) {
  currentPage.value = p
  if (viewMode.value === 'layout') pdfSoloRef.value?.goPage?.(p)
  else layoutBiRef.value?.goPage?.(p)
  progress.value = Math.min(100, Math.round((p / Math.max(pageTotal.value, 1)) * 100))
}

async function loadList() {
  const data = await api.get('/papers/', { params: { page_size: 100 } })
  paperList.value = data.results || data
}

async function loadPaper(id) {
  if (!id) return
  loading.value = true
  pipelineTip.value = ''
  try {
    paper.value = await api.get(`/papers/${id}/`)
    paperId.value = Number(id)
    progress.value = paper.value.read_progress || 0
    viewMode.value = 'layout-bi'
    const noteData = await api.get('/reader/notes/', { params: { paper: id, page_size: 50 } })
    notes.value = noteData?.results || noteData || []
    if (!props.embedded) {
      router.replace({ name: 'reader', params: { id: String(id) } })
    }
    // auto pipeline for PDF bilingual: layout → translate → ready to sync-highlight
    if (paper.value.has_pdf) {
      await ensurePipeline({ soft: true })
    }
  } catch (e) {
    ElMessage.error(e.message || '加载论文失败')
  } finally {
    loading.value = false
  }
}

async function ensurePipeline({ soft = false } = {}) {
  if (!paperId.value || !paper.value?.has_pdf) return
  pipelineBusy.value = true
  try {
    // ① layout parse
    if (!hasLayoutBlocks(paper.value)) {
      pipelineTip.value = '① 正在还原版面…'
      if (!paper.value.file_path && !paper.value.pdf_file_url) {
        paper.value = await api.post(`/papers/${paperId.value}/fetch-pdf/`, { parse_mode: 'ocr' })
      } else {
        paper.value = await api.post(`/papers/${paperId.value}/reparse/`, { parse_mode: 'ocr' })
      }
    }
    // ② translate text blocks (first page first when soft)
    const page = layoutBiRef.value?.page || 1
    const pendingPage = pendingTextCount(paper.value, page)
    const pendingAll = pendingTextCount(paper.value)
    if (pendingPage > 0 || (!soft && pendingAll > 0)) {
      translating.value = true
      pipelineTip.value = soft
        ? `② 正在翻译第 ${page} 页文本（${pendingPage || pendingAll} 块）…`
        : `② 正在翻译全文文本（${pendingAll} 块）…`
      await api.post('/reader/translate/paragraphs/', soft
        ? { paper: paperId.value, page }
        : { paper: paperId.value })
      paper.value = await api.get(`/papers/${paperId.value}/`)
    }
    pipelineTip.value = '③ 版面已就绪：点击 PDF 色块可对齐高亮译文'
    viewMode.value = 'layout-bi'
  } catch (e) {
    pipelineTip.value = ''
    if (!soft) ElMessage.error(e.message || '管线失败')
  } finally {
    translating.value = false
    pipelineBusy.value = false
  }
}

async function runPipeline() {
  await ensurePipeline({ soft: false })
  if (pipelineTip.value) ElMessage.success('解析→翻译→对照 已完成')
}

async function fetchPdf() {
  if (!paperId.value) return
  fetchingPdf.value = true
  try {
    paper.value = await api.post(`/papers/${paperId.value}/fetch-pdf/`, { parse_mode: 'ocr' })
    viewMode.value = 'layout-bi'
    ElMessage.success('PDF 已下载（PaddleOCR 版面还原）')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    fetchingPdf.value = false
  }
}

async function reparseLayout() {
  if (!paperId.value) return
  reparsing.value = true
  pipelineTip.value = '① PaddleOCR 正在还原版面…'
  try {
    paper.value = await api.post(`/papers/${paperId.value}/reparse/`, { parse_mode: 'ocr' })
    ElMessage.success('已用 PaddleOCR 还原版面')
    pipelineTip.value = '① 版面已还原，可继续翻译'
  } catch (e) {
    ElMessage.error(e.message)
    pipelineTip.value = ''
  } finally {
    reparsing.value = false
  }
}

async function onLayoutContext(payload) {
  if (payload?.close || payload?.index < 0) {
    if (bubble.show) closeBubble()
    return
  }
  const sel = window.getSelection()?.toString() || ''
  const changed = fillBubble(payload.index, payload.side, sel, { recenter: !bubble.show })
  if (bubble.show && changed === false) closeBubble()
}

async function onSelect(e, paraIndex, side) {
  if (ocrMode.value) return
  const sel = window.getSelection()?.toString() || ''
  const changed = fillBubble(paraIndex, side, sel, { recenter: !bubble.show })
  if (bubble.show && changed === false) closeBubble()
}

function onPaperPick(payload) {
  if (ocrMode.value) return
  if (!bubble.show || payload?.index < 0) return
  const sel = window.getSelection()?.toString() || ''
  fillBubble(payload.index, payload.side, sel, { recenter: false })
}

function pendingZh(zh) {
  const t = String(zh || '').trim()
  return !t || t.startsWith('（待') || t.includes('离线占位') || t.includes('【译文占位】')
}

function centerBubble() {
  bubble.x = Math.max(8, Math.round((window.innerWidth - 420) / 2))
  bubble.y = Math.max(8, Math.round((window.innerHeight - 440) / 2))
  nextTick(() => {
    const el = bubbleRef.value
    if (!el) return
    const w = el.offsetWidth || 420
    const h = el.offsetHeight || 420
    bubble.x = Math.max(8, Math.round((window.innerWidth - w) / 2))
    bubble.y = Math.max(8, Math.round((window.innerHeight - h) / 2))
  })
}

function clampBubble(x, y) {
  const el = bubbleRef.value
  const w = el?.offsetWidth || 420
  const h = el?.offsetHeight || 360
  const minX = 8 - Math.max(0, w - 80)
  const minY = 8
  const maxX = window.innerWidth - Math.min(w, 80)
  const maxY = window.innerHeight - 48
  bubble.x = Math.min(Math.max(minX, x), maxX)
  bubble.y = Math.min(Math.max(minY, y), maxY)
}

function isBubbleDragIgnore(el) {
  return !!el?.closest?.('textarea, input, button, select, .el-select, .el-button, .el-input')
}

function onBubblePointerDown(e) {
  if (e.button !== 0) return
  if (isBubbleDragIgnore(e.target)) return
  bubble.dragging = true
  bubbleDrag.dx = e.clientX - bubble.x
  bubbleDrag.dy = e.clientY - bubble.y
  e.currentTarget.setPointerCapture?.(e.pointerId)
}

function onBubblePointerMove(e) {
  if (!bubble.dragging) return
  clampBubble(e.clientX - bubbleDrag.dx, e.clientY - bubbleDrag.dy)
}

function onBubblePointerUp() {
  bubble.dragging = false
}

function closeBubble() {
  bubble.show = false
  bubble.dragging = false
  lastBubbleSel = ''
  bubbleAiToken += 1
  window.clearTimeout(bubbleSelTimer)
}

function readPaperSelection() {
  const selObj = window.getSelection()
  if (!selObj || selObj.rangeCount === 0 || selObj.isCollapsed) return null
  const sel = selObj.toString().replace(/\s+/g, ' ').trim()
  if (sel.length < 2) return null
  let node = selObj.anchorNode
  if (node && node.nodeType !== 1) node = node.parentElement
  if (!node || bubbleRef.value?.contains(node)) return null
  const block = node.closest?.('[data-bi], [data-i]')
  if (!block && !node.closest?.('.layout-bi')) return null
  const index = block != null ? Number(block.dataset.bi ?? block.dataset.i) : bubble.para_index
  const side = node.closest?.('.sheet.zh, .zh-col') ? 'zh' : 'en'
  return {
    sel,
    index: Number.isFinite(index) ? index : bubble.para_index,
    side,
  }
}

function followPaperSelection() {
  if (!bubble.show || bubble.dragging || ocrMode.value) return
  const ctx = readPaperSelection()
  if (!ctx) return
  fillBubble(ctx.index, ctx.side, ctx.sel, { recenter: false })
}

function scheduleBubbleAi(text, opts = {}) {
  window.clearTimeout(bubbleSelTimer)
  bubbleSelTimer = window.setTimeout(() => loadBubbleAi(text, opts), 280)
}

async function loadBubbleAi(text, { keepTranslation } = {}) {
  const token = ++bubbleAiToken
  if (!text || String(text).trim().length < 2) return
  bubble.loading = true
  try {
    const data = await api.post('/reader/translate/selection/', { text })
    if (token !== bubbleAiToken || !bubble.show) return
    if (!keepTranslation || !String(bubble.translation || '').trim()) {
      bubble.translation = data.translation
    }
    bubble.summary = data.summary
  } catch (err) {
    if (token === bubbleAiToken) ElMessage.error(err.message)
  } finally {
    if (token === bubbleAiToken) bubble.loading = false
  }
}

function fillBubble(index, side, rawSel, { recenter } = {}) {
  const para = paras.value[index] || {}
  const sel = String(rawSel || '').replace(/\s+/g, ' ').trim()
  const original = side === 'zh' ? (para.en || sel) : (sel || para.en || '')
  const translated = side === 'zh'
    ? (sel || (pendingZh(para.zh) ? '' : (para.zh || '')))
    : (sel ? '' : (pendingZh(para.zh) ? '' : (para.zh || '')))
  const key = `${index}|${side}|${sel || original}`
  if (bubble.show && key === lastBubbleSel) return false
  lastBubbleSel = key
  const first = !bubble.show
  bubble.text = original
  bubble.translation = translated
  bubble.summary = ''
  bubble.note = ''
  bubble.para_index = index ?? 0
  bubble.show = true
  if (first || recenter) centerBubble()
  layoutBiRef.value?.setActive?.(index)
  if (original && original.length >= 2) {
    scheduleBubbleAi(original, { keepTranslation: !!translated })
  }
  return true
}

async function regenBubble() {
  await loadBubbleAi(bubble.text, { keepTranslation: false })
}

async function saveNote() {
  await api.post('/reader/notes/', {
    paper: paperId.value,
    sel_text: String(bubble.text || '').slice(0, 1000),
    note_text: bubble.note || bubble.summary,
    ai_translation: bubble.translation,
    ai_summary: bubble.summary,
    visibility: bubble.visibility,
    para_index: bubble.para_index,
    source: 'selection',
  })
  ElMessage.success('笔记已保存')
  closeBubble()
  const noteData = await api.get('/reader/notes/', { params: { paper: paperId.value, page_size: 50 } })
  notes.value = noteData?.results || noteData || []
}

async function addHighlight(color) {
  await api.post('/reader/highlights/', {
    paper: paperId.value,
    para_index: bubble.para_index,
    sel_text: bubble.text,
    color,
  })
  ElMessage.success('已高亮')
}

async function translateAll() {
  translating.value = true
  try {
    const keep = viewMode.value
    await api.post('/reader/translate/paragraphs/', { paper: paperId.value })
    paper.value = await api.get(`/papers/${paperId.value}/`)
    viewMode.value = keep === 'layout' ? 'layout' : 'layout-bi'
    ElMessage.success('已按版面块一一对应完成翻译')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    translating.value = false
  }
}

async function translatePage(page) {
  translating.value = true
  pipelineTip.value = `② 正在翻译第 ${page} 页…`
  try {
    await api.post('/reader/translate/paragraphs/', { paper: paperId.value, page })
    paper.value = await api.get(`/papers/${paperId.value}/`)
    pipelineTip.value = '③ 本页译文已更新，可点击 PDF 色块对齐'
    ElMessage.success(`第 ${page} 页已对齐翻译`)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    translating.value = false
  }
}

const bodyClass = computed(() => {
  const parts = ['layout-only']
  if (aiCollapsed.value) parts.push('ai-collapsed')
  if (pagesCollapsed.value) parts.push('pages-collapsed')
  return parts.join(' ')
})

watch(aiCollapsed, (v) => {
  localStorage.setItem('pm_ai_collapsed', v ? '1' : '0')
})
watch(pagesCollapsed, (v) => {
  localStorage.setItem('pm_pages_collapsed', v ? '1' : '0')
})
watch(leftTab, (v) => {
  localStorage.setItem('pm_left_tab', v)
})

function jumpNote(n) {
  flashIndex.value = n.para_index
  layoutBiRef.value?.goBlock?.(n.para_index)
}


async function genSummary() {
  summarizing.value = true
  try {
    const data = await api.post('/ai/summarize/', { paper: paperId.value })
    paper.value.ai_summary = data
    aiCollapsed.value = false
    aiTab.value = 'sum'
    ElMessage.success('总结已生成')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    summarizing.value = false
  }
}

async function ask() {
  const q = question.value.trim()
  if (!q || asking.value) return
  asking.value = true
  aiTab.value = 'chat'
  chat.value = [...chat.value, { role: 'user', content: q }]
  question.value = ''
  scrollChat()
  try {
    const data = await api.post('/ai/ask/', {
      paper: paperId.value,
      question: q,
      conversation_id: conversationId.value,
    })
    conversationId.value = data.conversation_id
    chat.value = data.messages || []
    scrollChat()
  } catch (e) {
    ElMessage.error(e.message || '提问失败')
  } finally {
    asking.value = false
    scrollChat()
  }
}

function quickAsk(text) {
  question.value = text
  ask()
}

function formatMsg(text) {
  let s = String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>')
  s = s.replace(/^\s*[-*]\s+/gm, '• ')
  return s.replace(/\n/g, '<br>')
}

function scrollChat() {
  nextTick(() => {
    const el = chatRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function jumpSection(o) {
  activeSection.value = o.id
  if (o.page) currentPage.value = o.page
  if (viewMode.value === 'layout') {
    if (o.page) pdfSoloRef.value?.goPage?.(o.page)
    if (o.para_index != null) pdfSoloRef.value?.highlightBlock?.(o.para_index)
    return
  }
  layoutBiRef.value?.goBlock?.(o.para_index)
}

function onActivePara(index) {
  let cur = ''
  for (const o of tocItems.value) {
    if (Number(o.para_index) <= Number(index)) cur = o.id
  }
  if (cur) activeSection.value = cur
}


async function onOcrFile(e) {
  const file = e.target.files?.[0]
  if (!file || !paperId.value) return
  await uploadOcrImage(file, '')
  e.target.value = ''
}

function toggleOcrMode() {
  ocrMode.value = !ocrMode.value
  ocrBox.show = false
  if (ocrMode.value) {
    closeBubble()
    ElMessage.info('在左侧原文 PDF 上拖拽框选区域')
  } else {
    stopOcrDrag()
  }
}

function stopOcrDrag() {
  window.removeEventListener('mousemove', onOcrMove)
  window.removeEventListener('mouseup', onOcrUp)
}

function onOcrDown(e) {
  if (ocrBusy.value || e.button !== 0) return
  ocrBox.show = true
  ocrBox.x0 = e.clientX
  ocrBox.y0 = e.clientY
  ocrBox.x1 = e.clientX
  ocrBox.y1 = e.clientY
  window.addEventListener('mousemove', onOcrMove)
  window.addEventListener('mouseup', onOcrUp)
}

function onOcrMove(e) {
  ocrBox.x1 = e.clientX
  ocrBox.y1 = e.clientY
}

async function onOcrUp() {
  stopOcrDrag()
  const left = Math.min(ocrBox.x0, ocrBox.x1)
  const top = Math.min(ocrBox.y0, ocrBox.y1)
  const width = Math.abs(ocrBox.x1 - ocrBox.x0)
  const height = Math.abs(ocrBox.y1 - ocrBox.y0)
  ocrBox.show = false
  if (width < 12 || height < 12) {
    ElMessage.warning('框选区域太小，请再试一次')
    return
  }
  try {
    const blob = await capturePageRect(left, top, width, height)
    if (ocrResult.preview) URL.revokeObjectURL(ocrResult.preview)
    ocrResult.preview = URL.createObjectURL(blob)
    await uploadOcrImage(blob, `${Math.round(width)}×${Math.round(height)} px`)
  } catch (err) {
    ElMessage.error(err.message || '截图失败')
  }
}

async function capturePageRect(left, top, width, height) {
  const imgs = [...document.querySelectorAll('.reader img.page-img')]
    .filter((img) => img.naturalWidth > 0)
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(width * dpr))
  canvas.height = Math.max(1, Math.round(height * dpr))
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  let painted = false
  for (const img of imgs) {
    const r = img.getBoundingClientRect()
    const ix = Math.max(left, r.left)
    const iy = Math.max(top, r.top)
    const ix2 = Math.min(left + width, r.right)
    const iy2 = Math.min(top + height, r.bottom)
    if (ix2 - ix < 2 || iy2 - iy < 2) continue
    const scaleX = img.naturalWidth / r.width
    const scaleY = img.naturalHeight / r.height
    ctx.drawImage(
      img,
      (ix - r.left) * scaleX,
      (iy - r.top) * scaleY,
      (ix2 - ix) * scaleX,
      (iy2 - iy) * scaleY,
      (ix - left) * dpr,
      (iy - top) * dpr,
      (ix2 - ix) * dpr,
      (iy2 - iy) * dpr,
    )
    painted = true
  }
  if (!painted) {
    throw new Error('请在左侧原文 PDF 上框选（不要框选译文空白处）')
  }
  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('截图生成失败'))), 'image/png')
  })
  return blob
}

async function uploadOcrImage(file, rect) {
  if (!paperId.value) return
  ocrBusy.value = true
  try {
    const shot = file instanceof File
      ? file
      : new File([file], 'screenshot.png', { type: file.type || 'image/png' })
    const fd = new FormData()
    fd.append('image', shot)
    fd.append('paper', String(paperId.value))
    fd.append('rect', rect || '')
    const data = await api.post('/reader/ocr/', fd)
    Object.assign(ocrResult, data)
    if (!ocrResult.preview && ocrResult.image_path) {
      ocrResult.preview = String(ocrResult.image_path).startsWith('/media')
        ? ocrResult.image_path
        : `/media/${ocrResult.image_path}`
    }
    ocrResult.note = ocrResult.note || ''
    ocrDialog.value = true
    ocrMode.value = false
  } catch (err) {
    ElMessage.error(err.message || 'OCR 失败')
  } finally {
    ocrBusy.value = false
  }
}

async function saveOcrNote() {
  await api.post('/reader/notes/', {
    paper: paperId.value,
    sel_text: String(ocrResult.ocr_text || '').slice(0, 1000),
    note_text: ocrResult.note || ocrResult.ai_summary || '截图OCR笔记',
    ai_translation: ocrResult.ai_translation,
    ai_summary: ocrResult.ai_summary,
    source: 'ocr',
    ocr_image_path: ocrResult.image_path,
    ocr_rect: ocrResult.rect,
    visibility: 'public',
  })
  ElMessage.success('OCR 笔记已保存')
  ocrDialog.value = false
  const noteData = await api.get('/reader/notes/', { params: { paper: paperId.value, page_size: 50 } })
  notes.value = noteData?.results || noteData || []
}

function onKey(e) {
  if (e.key === 'Escape') {
    ocrMode.value = false
    ocrBox.show = false
    stopOcrDrag()
    closeBubble()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  document.addEventListener('mouseup', followPaperSelection)
  document.addEventListener('selectionchange', followPaperSelection)
  await loadList()
  const id = Number(props.initialPaperId || route.params.id || route.query.p) || paperList.value[0]?.id
  if (id) await loadPaper(id)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  document.removeEventListener('mouseup', followPaperSelection)
  document.removeEventListener('selectionchange', followPaperSelection)
  stopOcrDrag()
  window.clearTimeout(bubbleSelTimer)
  if (ocrResult.preview && ocrResult.preview.startsWith('blob:')) {
    URL.revokeObjectURL(ocrResult.preview)
  }
})

watch(() => route.params.id, (id) => { if (id && !props.embedded) loadPaper(Number(id)) })
watch(() => props.initialPaperId, (id) => { if (id) loadPaper(Number(id)) })

defineExpose({ loadPaper, loadList })
</script>

<style scoped>
.reader {
  display: flex; flex-direction: column;
  height: 100%; min-height: 0;
  padding: 0 12px 12px;
  overflow: hidden;
}
.toolbar {
  position: sticky; top: 0; z-index: 30;
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
  padding: 10px 14px; margin: 8px 0 10px;
  flex: none;
  background: #fff;
}
.body {
  flex: 1; min-height: 0;
  display: grid; grid-template-columns: auto 1fr auto; gap: 12px;
  position: relative;
}
.ocr-mask {
  grid-column: 2;
  grid-row: 1;
  z-index: 80;
  min-height: 0;
  position: relative;
  cursor: crosshair;
  background: rgba(15, 23, 42, 0.28);
  user-select: none;
}
.ocr-mask.busy { cursor: wait; pointer-events: none; }
.ocr-hint {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: #111827;
  color: #fff;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  pointer-events: none;
  white-space: nowrap;
}
.ocr-rect {
  position: fixed;
  z-index: 81;
  border: 2px solid #60a5fa;
  background: rgba(96, 165, 250, 0.18);
  pointer-events: none;
  box-sizing: border-box;
}
.ocr-meta { font-size: 13px; color: var(--text-2); margin-bottom: 10px; }
.ocr-preview {
  margin-bottom: 12px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  background: #f8fafc;
  max-height: 180px;
  overflow: auto;
  text-align: center;
}
.ocr-preview img { max-width: 100%; max-height: 170px; display: inline-block; }
.body.layout-only { grid-template-columns: auto 1fr auto; }
.body.ai-collapsed { grid-template-columns: auto 1fr auto; }
.page-dock {
  display: flex;
  min-width: 28px;
  width: 196px;
  min-height: 0;
  height: 100%;
  transition: width .18s ease;
}
.page-dock.collapsed { width: 28px; }
.left-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  margin-bottom: 8px;
}
.left-tabs button {
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 8px;
  padding: 5px 0;
  font-size: 12.5px;
  color: var(--text-2);
  cursor: pointer;
}
.left-tabs button.active {
  background: var(--primary-light);
  color: var(--primary);
  border-color: var(--primary);
  font-weight: 600;
}
.toc-list { padding: 0 2px 8px; }
.toc-empty { font-size: 12px; color: var(--text-3); line-height: 1.5; padding: 8px 4px; }
.ol-item { padding: 6px 8px; border-radius: 6px; cursor: pointer; color: var(--text-2); font-size: 13px; }
.ol-item:hover, .ol-item.active { background: var(--primary-light); color: var(--primary); }
.ol-item.h2 { padding-left: 16px; font-size: 12.5px; }
.page-panel {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: 8px 6px;
  border-radius: 12px 0 0 12px;
  border-right: none;
}
.page-panel-title {
  font-size: 12px; color: var(--text-2); text-align: center; margin-bottom: 8px;
}
.thumb {
  margin-bottom: 8px; border: 2px solid transparent; border-radius: 6px;
  cursor: pointer; overflow: hidden; background: #fff; text-align: center;
  font-size: 12px; color: var(--text-3);
}
.thumb.active { border-color: var(--primary); }
.thumb img { width: 100%; display: block; }
.page-handle {
  flex: none;
  width: 28px;
  border: 1px solid var(--border);
  border-radius: 0 10px 10px 0;
  background: #fff;
  color: var(--text-2);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 0;
}
.page-dock:not(.collapsed) .page-handle { border-left: none; }
.page-dock.collapsed .page-handle { border-radius: 10px; }
.page-handle:hover { background: var(--primary-light); color: var(--primary); }
.outline, .content { overflow: auto; padding: 14px; min-height: 0; }
.pdf-pane { padding: 0; overflow: hidden; display: flex; flex-direction: column; }
.ai-dock {
  display: flex;
  min-width: 28px;
  width: 360px;
  min-height: 0;
  height: 100%;
  transition: width .18s ease;
}
.ai-dock.collapsed { width: 28px; }
.ai-handle {
  flex: none;
  width: 28px;
  border: 1px solid var(--border);
  border-radius: 10px 0 0 10px;
  background: #fff;
  color: var(--text-2);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 0;
}
.ai-dock:not(.collapsed) .ai-handle {
  border-right: none;
  border-radius: 10px 0 0 10px;
}
.ai-dock.collapsed .ai-handle {
  border-radius: 10px;
  width: 28px;
}
.ai-handle:hover { background: var(--primary-light); color: var(--primary); }
.ai-handle-icon { font-size: 16px; font-weight: 700; line-height: 1; }
.ai-handle-label {
  writing-mode: vertical-rl;
  letter-spacing: 3px;
  font-size: 13px;
  font-weight: 600;
}
.ai-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  border-radius: 0 12px 12px 0;
  border-left: none;
  background: #fff;
}
.ai-head { padding: 14px 16px 8px; }
.ai-head-title { font-size: 15px; font-weight: 700; color: #111827; }
.ai-head-sub { font-size: 12px; color: var(--text-3); margin-top: 2px; }
.ai-tabs {
  display: flex;
  gap: 4px;
  padding: 0 12px 10px;
  border-bottom: 1px solid var(--border);
}
.ai-tabs button {
  flex: 1;
  border: 0;
  background: transparent;
  padding: 7px 0;
  font-size: 13px;
  color: var(--text-2);
  border-radius: 8px;
  cursor: pointer;
}
.ai-tabs button.active {
  background: var(--primary-light);
  color: var(--primary);
  font-weight: 600;
}
.tab-n {
  display: inline-block;
  min-width: 16px;
  padding: 0 5px;
  margin-left: 2px;
  border-radius: 999px;
  background: var(--primary);
  color: #fff;
  font-size: 11px;
  line-height: 16px;
}
.ai-chat, .ai-extra {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.ai-extra { overflow: auto; padding: 12px; }
.chat-msgs {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 48px);
}
.chat-empty {
  margin: auto;
  text-align: center;
  color: var(--text-3);
  font-size: 13px;
  padding: 20px 8px;
}
.chat-empty-icon {
  width: 40px; height: 40px; margin: 0 auto 10px;
  border-radius: 12px;
  background: var(--primary-light);
  color: var(--primary);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-top: 12px; }
.chip {
  border: 1px solid var(--border);
  background: #fff;
  color: var(--primary);
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
}
.chip:hover { background: var(--primary-light); border-color: var(--primary); }
.msg { display: flex; flex-direction: column; max-width: 92%; }
.msg.user { align-self: flex-end; align-items: flex-end; }
.msg.assistant { align-self: flex-start; align-items: flex-start; }
.msg-who { font-size: 11px; color: var(--text-3); margin-bottom: 4px; }
.msg-bubble {
  padding: 9px 12px;
  border-radius: 14px;
  font-size: 13.5px;
  line-height: 1.65;
  word-break: break-word;
}
.msg.user .msg-bubble {
  background: var(--primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg.assistant .msg-bubble {
  background: #f1f4f9;
  color: #1f2937;
  border-bottom-left-radius: 4px;
}
.msg-bubble :deep(strong) { font-weight: 700; }
.msg-bubble :deep(code) {
  font-size: 12px;
  background: rgba(0,0,0,.06);
  padding: 1px 5px;
  border-radius: 4px;
}
.msg.user .msg-bubble :deep(code) { background: rgba(255,255,255,.2); }
.typing { display: flex; gap: 4px; align-items: center; min-width: 42px; }
.typing span {
  width: 6px; height: 6px; border-radius: 50%; background: #94a3b8;
  animation: typing 1s infinite ease-in-out;
}
.typing span:nth-child(2) { animation-delay: .15s; }
.typing span:nth-child(3) { animation-delay: .3s; }
@keyframes typing {
  0%, 80%, 100% { opacity: .35; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-3px); }
}
.composer {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 10px 12px 12px;
  border-top: 1px solid var(--border);
  background: #fff;
}
.composer :deep(.el-textarea) { flex: 1; }
.composer :deep(.el-textarea__inner) {
  border-radius: 12px;
  box-shadow: none;
  min-height: 64px;
}
.composer :deep(.el-button) {
  height: 40px;
  border-radius: 10px;
  padding: 0 16px;
}
.sum-card h5 { font-size: 12px; color: var(--primary); margin: 0 0 6px; }
.sum-sec {
  padding: 10px 0;
  border-bottom: 1px dashed var(--border);
}
.sum-sec:first-child { padding-top: 0; }
.sum-sec:last-of-type { border-bottom: 0; }
.sum-zh { font-size: 13.5px; line-height: 1.7; color: #1f2937; margin: 0; }
.sum-en { font-size: 12.5px; line-height: 1.65; color: #6b7280; margin: 4px 0 0; }
.sum-list { margin: 0; padding-left: 18px; }
.sum-list li { margin-bottom: 8px; }
.sum-list li:last-child { margin-bottom: 0; }
.sum-term { margin-bottom: 8px; }
.sum-term-en { font-weight: 650; color: #111827; font-size: 13px; }
.sum-term-zh { margin-left: 6px; color: var(--primary); font-size: 12.5px; }
.sum-hint { font-size: 12px; color: var(--text-3); margin: 8px 0 10px; }
.note-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: pointer;
  background: #fff;
}
.note-card:hover { border-color: #bfdbfe; background: #f8fafc; }
.note-main { font-size: 13px; color: #1f2937; line-height: 1.55; }
.note-src { font-size: 12px; color: var(--text-3); margin-top: 6px; }
.bubble {
  position: fixed; z-index: 100; width: 420px; padding: 0 14px 12px;
  box-shadow: var(--shadow-lg);
  max-height: min(520px, calc(100vh - 24px));
  overflow: auto;
  touch-action: none;
}
.bubble.dragging { cursor: grabbing; user-select: none; }
.bubble-head {
  font-weight: 600; margin: 0 -14px 10px; padding: 12px 14px 10px;
  font-size: 13.5px; cursor: grab; display: flex; align-items: center; gap: 8px;
  user-select: none;
}
.bubble-head:active, .bubble.dragging .bubble-head { cursor: grabbing; }
.bubble-drag { color: var(--text-3); letter-spacing: -2px; font-size: 14px; }
.bubble-lab { font-size: 12px; color: var(--text-3); margin: 0 0 4px; }
.bubble textarea {
  width: 100%; box-sizing: border-box;
  min-height: 52px; padding: 8px; border: 1px solid var(--border);
  border-radius: 8px; margin-bottom: 8px; outline: none; resize: vertical;
  font-size: 13px; line-height: 1.55; font-family: inherit;
}
.bubble textarea:focus { border-color: var(--primary); }
.bubble-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.empty { padding: 40px; text-align: center; }
.muted { color: var(--text-3); font-size: 13px; }
.pipe-tip {
  font-size: 12.5px; color: var(--primary);
  background: var(--primary-light); padding: 4px 10px; border-radius: 999px;
}
@media (max-width: 1100px) {
  .body, .body.layout-only, .body.ai-collapsed, .body.layout-only.ai-collapsed {
    grid-template-columns: 1fr; height: auto;
  }
  .reader { height: auto; overflow: visible; }
  .ai-dock, .page-dock { min-height: 48px; width: 100%; }
  .ai-handle, .page-handle { flex-direction: row; width: 100%; }
  .ai-handle-label { writing-mode: horizontal-tb; }
}
</style>
