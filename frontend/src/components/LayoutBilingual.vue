<template>
  <div class="layout-bi" @contextmenu.prevent>
    <div class="bi-bar">
      <span class="pg">第 {{ page }} / {{ pageCount }} 页</span>
      <el-button size="small" @click="zoomOut">−</el-button>
      <span class="pg">{{ Math.round(zoom * 100) }}%</span>
      <el-button size="small" @click="zoomIn">＋</el-button>
      <el-button size="small" @click="fitWidth">适宽</el-button>
      <el-button size="small" type="primary" :loading="translating" @click="translatePage">翻译当前页</el-button>
      <span class="muted">右击打开气泡后，再点选/划选其他原文或译文会同步更新 · 右击空白或 Esc 关闭</span>
    </div>

    <div class="bi-scroll" ref="scrollRef" @scroll="onScroll" @mouseup="onRootMouseUp">
      <div class="bi-track" :style="{ width: trackW + 'px' }">
        <div
          v-for="pg in pages"
          :key="pg.page"
          :id="'bi-page-' + pg.page"
          class="page-pair"
          :data-page="pg.page"
        >
          <div class="sheet orig" :style="{ width: pageW + 'px', height: pg.h + 'px' }" @contextmenu.prevent="onBlankCtx">
            <img
              v-if="pageImgs[pg.page] || pg.thumb"
              class="page-img"
              :src="pageImgs[pg.page] || pg.thumb"
              alt=""
              draggable="false"
            />
            <div class="overlay">
              <div
                v-for="b in overlaysFor(pg.page)"
                :key="b.index"
                :data-bi="b.index"
                class="bbox"
                :class="{ active: active === b.index }"
                :style="b.style"
                :title="b.title"
                @click.stop="setActive(b.index)"
                @mouseenter="active = b.index"
                @contextmenu.prevent.stop="onCtx($event, b.index, 'en')"
              >
                <span class="ghost-en" :style="{ fontSize: b.fontSize + 'px' }">{{ b.en }}</span>
              </div>
            </div>
          </div>
          <div class="sheet zh" :style="{ width: pageW + 'px', height: pg.h + 'px' }" @contextmenu.prevent="onBlankCtx">
            <div
              v-for="b in laidFor(pg.page)"
              :key="b.index"
              :data-bi="b.index"
              class="cell"
              :class="{ active: active === b.index, pending: b.pending }"
              :style="b.style"
              @mouseenter="active = b.index"
              @click="setActive(b.index)"
              @contextmenu.prevent.stop="onCtx($event, b.index, 'zh')"
            >
              <img
                v-if="b.type === 'figure' && b.image"
                :src="b.image"
                class="fig"
                @click.stop="$emit('preview', b.image)"
              />
              <div v-else class="txt" :style="{ fontSize: b.fontSize + 'px' }">{{ b.text }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  fileUrl: String,
  paperId: { type: [Number, String], default: null },
  layoutMeta: Object,
  paras: { type: Array, default: () => [] },
  translating: Boolean,
  initialPage: { type: Number, default: 1 },
})

const emit = defineEmits(['page-change', 'translate-page', 'preview', 'active-change', 'context', 'pick'])

const auth = useAuthStore()
const scrollRef = ref(null)
const page = ref(props.initialPage || 1)
const active = ref(-1)
const zoom = ref(1)
const pageW = ref(480)
const pageImgs = reactive({})
const objectUrls = []
let loadToken = 0

const pageCount = computed(() => {
  const n = props.layoutMeta?.page_count || (props.layoutMeta?.pages || []).length
  return n || 1
})

const pages = computed(() => {
  const meta = props.layoutMeta?.pages || []
  const list = meta.length
    ? meta.map((p) => ({
        page: Number(p.page),
        pdfW: Number(p.width) || 612,
        pdfH: Number(p.height) || 792,
        thumb: mediaSrc(p.preview || p.thumb),
      }))
    : Array.from({ length: pageCount.value }, (_, i) => ({
        page: i + 1, pdfW: 612, pdfH: 792, thumb: '',
      }))
  return list.map((p) => ({
    ...p,
    h: Math.round(pageW.value * (p.pdfH / p.pdfW)),
  }))
})

const trackW = computed(() => pageW.value * 2 + 24)

function mediaSrc(rel) {
  if (!rel) return ''
  if (rel.startsWith('/media') || rel.startsWith('http') || rel.startsWith('blob:')) return rel
  return `/media/${rel}`
}

function mediaUrl(para) {
  if (para.image_url) return para.image_url
  if (para.image) return para.image.startsWith('/media') ? para.image : `/media/${para.image}`
  return ''
}

function isPending(para) {
  if ((para.type || 'text') === 'figure') return false
  const zh = String(para.zh || '').trim()
  return !zh || zh.startsWith('（待') || zh.includes('离线占位') || zh.includes('【译文占位】')
}

function fitFont(text, w, h) {
  const t = String(text || '')
  const chars = Math.max(t.length, 1)
  const maxFs = Math.min(h * 0.92, 18)
  let fs = maxFs
  for (let i = 0; i < 8; i++) {
    const perLine = Math.max(1, Math.floor(w / Math.max(fs * 0.95, 6)))
    const lines = Math.ceil(chars / perLine)
    if (lines * fs * 1.28 <= h * 1.05 || fs <= 8) break
    fs *= 0.88
  }
  return Math.max(7.5, Math.min(maxFs, fs))
}

function laidFor(pageNo) {
  const meta = pages.value.find((p) => p.page === pageNo)
  const pw = meta?.pdfW || 612
  const ph = meta?.pdfH || 792
  const sx = pageW.value / pw
  const sy = (meta?.h || pageW.value) / ph
  return props.paras
    .map((para, index) => ({ para, index }))
    .filter((x) => Number(x.para.page || 0) === Number(pageNo))
    .map(({ para, index }) => {
      const type = para.type || 'text'
      const pending = isPending(para)
      const bbox = Array.isArray(para.bbox) && para.bbox.length >= 4 ? para.bbox.map(Number) : null
      let left = 12
      let top = 12 + index * 22
      let width = pageW.value - 24
      let height = 20
      if (bbox) {
        left = Math.min(bbox[0], bbox[2]) * sx
        top = Math.min(bbox[1], bbox[3]) * sy
        width = Math.max(8, Math.abs(bbox[2] - bbox[0]) * sx)
        height = Math.max(10, Math.abs(bbox[3] - bbox[1]) * sy)
      }
      const text = type === 'figure'
        ? (para.zh || '[图]')
        : (pending ? '（待翻译）' : String(para.zh || '').trim())
      return {
        index,
        type,
        pending,
        text,
        image: mediaUrl(para),
        fontSize: fitFont(text, width, height),
        style: {
          left: `${left}px`,
          top: `${top}px`,
          width: `${width}px`,
          height: `${height}px`,
        },
      }
    })
}

function overlaysFor(pageNo) {
  const meta = pages.value.find((p) => p.page === pageNo)
  const pw = meta?.pdfW || 612
  const ph = meta?.pdfH || 792
  const sx = pageW.value / pw
  const sy = (meta?.h || pageW.value) / ph
  return props.paras
    .map((para, index) => ({ para, index }))
    .filter((x) => Number(x.para.page || 0) === Number(pageNo))
    .filter((x) => Array.isArray(x.para.bbox) && x.para.bbox.length >= 4)
    .map(({ para, index }) => {
      const [x0, y0, x1, y1] = para.bbox.map(Number)
      const left = Math.min(x0, x1) * sx
      const top = Math.min(y0, y1) * sy
      const width = Math.abs(x1 - x0) * sx
      const height = Math.abs(y1 - y0) * sy
      if (width < 2 || height < 2) return null
      if (width > pageW.value * 0.98 && height > (meta?.h || 1) * 0.55) return null
      const en = String(para.en || '')
      return {
        index,
        title: en.slice(0, 80),
        en,
        fontSize: fitFont(en, width, height),
        style: { left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px` },
      }
    })
    .filter(Boolean)
}

function applyWidth() {
  const el = scrollRef.value
  if (!el) return
  const avail = Math.max(320, el.clientWidth - 36)
  pageW.value = Math.round((avail / 2) * zoom.value)
}

function zoomIn() { zoom.value = Math.min(1.8, +(zoom.value + 0.1).toFixed(2)); nextTick(applyWidth) }
function zoomOut() { zoom.value = Math.max(0.55, +(zoom.value - 0.1).toFixed(2)); nextTick(applyWidth) }
function fitWidth() { zoom.value = 1; nextTick(applyWidth) }

function setActive(index) {
  active.value = index
  emit('active-change', index)
}

function onCtx(e, index, side) {
  emit('context', { event: e, index, side, x: e.clientX, y: e.clientY })
}

function onBlankCtx(e) {
  emit('context', { event: e, index: -1, side: '', x: e.clientX, y: e.clientY, close: true })
}

function onRootMouseUp(e) {
  if (e.button !== 0) return
  const block = e.target?.closest?.('[data-bi]')
  if (!block) return
  const side = e.target.closest('.sheet.zh') ? 'zh' : 'en'
  const index = Number(block.dataset.bi)
  if (!Number.isFinite(index)) return
  setActive(index)
  emit('pick', { event: e, index, side })
}

function translatePage() {
  emit('translate-page', page.value)
}

function goPage(p) {
  const n = Math.min(Math.max(1, Number(p) || 1), pageCount.value)
  page.value = n
  emit('page-change', n)
  nextTick(() => {
    const root = scrollRef.value
    const el = document.getElementById(`bi-page-${n}`)
    if (root && el) root.scrollTop = el.offsetTop - 8
  })
}

function goBlock(index) {
  const para = props.paras[index]
  if (!para) return
  setActive(index)
  const p = Number(para.page || 1)
  page.value = Math.min(Math.max(1, p), pageCount.value)
  emit('page-change', page.value)
  nextTick(() => {
    const root = scrollRef.value
    const pair = document.getElementById(`bi-page-${page.value}`)
    if (!root || !pair) return
    const cell = pair.querySelector(`.sheet.zh [data-bi="${index}"]`) || pair.querySelector(`[data-bi="${index}"]`)
    if (cell) {
      const rootRect = root.getBoundingClientRect()
      const cellRect = cell.getBoundingClientRect()
      root.scrollTop += cellRect.top - rootRect.top - 32
    } else {
      root.scrollTop = Math.max(0, pair.offsetTop - 8)
    }
  })
}

function onScroll() {
  const root = scrollRef.value
  if (!root) return
  const mid = root.scrollTop + root.clientHeight * 0.35
  let current = 1
  for (const node of root.querySelectorAll('.page-pair')) {
    const top = node.offsetTop
    const bottom = top + node.offsetHeight
    if (mid >= top && mid < bottom) {
      current = Number(node.dataset.page)
      break
    }
  }
  if (current !== page.value) {
    page.value = current
    emit('page-change', current)
  }
}

async function loadPageImg(pageNo) {
  const id = Number(props.paperId)
  if (!id || pageImgs[pageNo]) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const meta = pages.value.find((p) => p.page === pageNo)
  const pdfW = meta?.pdfW || 612
  const zoomScale = Math.min(4.5, Math.max(2, (pageW.value * dpr * 1.2) / pdfW))
  try {
    const res = await fetch(`/api/papers/${id}/page-image/?page=${pageNo}&scale=${zoomScale}`, {
      headers: { Authorization: `Bearer ${auth.access}` },
    })
    if (!res.ok) return
    const url = URL.createObjectURL(await res.blob())
    objectUrls.push(url)
    pageImgs[pageNo] = url
  } catch { /* ignore */ }
}

async function loadVisibleAndAround() {
  const t = ++loadToken
  const cur = page.value
  const order = [cur, cur + 1, cur - 1, cur + 2, cur - 2]
    .filter((n) => n >= 1 && n <= pageCount.value)
  for (const n of order) {
    if (t !== loadToken) return
    await loadPageImg(n)
  }
  for (let n = 1; n <= pageCount.value; n++) {
    if (t !== loadToken) return
    if (!pageImgs[n]) await loadPageImg(n)
  }
}

watch(page, () => loadVisibleAndAround())
watch(() => props.paperId, () => {
  Object.keys(pageImgs).forEach((k) => delete pageImgs[k])
  loadVisibleAndAround()
})
watch(() => props.initialPage, (p) => { if (p) goPage(p) })

onMounted(() => {
  applyWidth()
  window.addEventListener('resize', applyWidth)
  loadVisibleAndAround()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', applyWidth)
  objectUrls.forEach((u) => URL.revokeObjectURL(u))
})

defineExpose({ page, active, goPage, goBlock, setActive })
</script>

<style scoped>
.layout-bi {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #525659;
}
.bi-bar {
  flex: none;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 8px 12px; background: #fff; border-bottom: 1px solid var(--border);
}
.pg { font-size: 13px; color: var(--text-2); min-width: 48px; text-align: center; }
.muted { font-size: 12px; color: var(--text-3); }
.bi-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 12px 40px;
}
.bi-track { margin: 0 auto; }
.page-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 18px;
}
.sheet {
  position: relative;
  background: #fff;
  box-shadow: 0 4px 18px rgba(0,0,0,.28);
  overflow: hidden;
}
.page-img { display: block; width: 100%; height: 100%; object-fit: fill; user-select: none; }
.overlay { position: absolute; inset: 0; pointer-events: none; }
.bbox {
  position: absolute; pointer-events: auto; padding: 0; border: 1px solid transparent;
  background: transparent; cursor: text; box-sizing: border-box; overflow: hidden;
}
.bbox:hover { background: rgba(37,99,235,.1); border-color: rgba(37,99,235,.55); }
.bbox.active { background: rgba(37,99,235,.16); border-color: #2563eb; z-index: 2; }
.ghost-en {
  display: block; width: 100%; height: 100%;
  color: transparent; caret-color: #2563eb;
  user-select: text; overflow: hidden; word-break: break-word;
  line-height: 1.25; font-family: "Times New Roman", Times, serif;
}
.cell {
  position: absolute; overflow: hidden; cursor: text;
  box-sizing: border-box; border: 1px solid transparent; padding: 0 1px;
  user-select: text;
}
.cell:hover { background: rgba(37,99,235,.08); border-color: rgba(37,99,235,.35); }
.cell.active { background: rgba(37,99,235,.14); border-color: #2563eb; z-index: 2; }
.cell.pending .txt { color: #b45309; }
.txt {
  color: #111827;
  font-family: "Source Han Serif SC", "Noto Serif SC", "Songti SC", "SimSun", serif;
  overflow: hidden; word-break: break-word; line-height: 1.25;
  user-select: text; -webkit-user-select: text;
}
.fig { width: 100%; height: 100%; object-fit: contain; display: block; }
</style>
