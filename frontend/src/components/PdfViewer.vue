<template>
  <div class="pdf-viewer" :class="{ 'no-thumbs': !showThumbs }">
    <div class="pdf-bar">
      <el-button size="small" :disabled="page<=1" @click="goPage(page-1)">‹ 上一页</el-button>
      <span class="pg">{{ page }} / {{ pageCount || '…' }}</span>
      <el-button size="small" :disabled="page>=pageCount" @click="goPage(page+1)">下一页 ›</el-button>
      <el-button size="small" @click="zoomOut">−</el-button>
      <span class="pg">{{ Math.round(scale * 100) }}%</span>
      <el-button size="small" @click="zoomIn">＋</el-button>
      <el-button size="small" @click="fitWidth">适宽</el-button>
      <el-switch
        v-if="interactive && showThumbs"
        v-model="showBoxes"
        size="small"
        inline-prompt
        active-text="块"
        inactive-text="净"
      />
      <a v-if="pdfBlobUrl" class="open-raw" :href="pdfBlobUrl" target="_blank" rel="noopener">↗ 原版</a>
      <span v-if="error" class="err">{{ error }}</span>
    </div>

    <div class="pdf-stage" ref="stageRef">
      <div v-if="!pageImg && loading" class="hint">正在加载 PDF 原页…</div>
      <div
        v-show="pageImg"
        class="page-wrap"
        ref="pageWrapRef"
        :style="{ width: displayWidth + 'px' }"
      >
        <img
          class="page-img"
          :src="pageImg"
          alt="PDF 原页"
          draggable="false"
        />
        <div
          v-if="interactive && showBoxes"
          class="overlay-layer"
        >
          <button
            v-for="b in pageOverlays"
            :key="b.index"
            type="button"
            class="bbox"
            :class="[b.type, { active: b.index === activeIndex }]"
            :style="b.style"
            :title="b.title"
            @click.stop="onOverlayClick(b)"
            @mouseenter="emit('hover-block', b.index)"
          />
        </div>
      </div>
    </div>

    <aside v-if="showThumbs && thumbs.length" class="thumbs">
      <div
        v-for="t in thumbs"
        :key="t.page"
        class="thumb"
        :class="{ active: t.page === page }"
        @click="goPage(t.page)"
      >
        <img v-if="t.url" :src="t.url" :alt="'p'+t.page" />
        <span v-else>{{ t.page }}</span>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  fileUrl: { type: String, default: '' },
  paperId: { type: [Number, String], default: null },
  layoutMeta: { type: Object, default: null },
  blocks: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: -1 },
  interactive: { type: Boolean, default: false },
  showThumbs: { type: Boolean, default: true },
  initialPage: { type: Number, default: 1 },
})

const emit = defineEmits(['page-change', 'ready', 'select-block', 'hover-block', 'metrics'])

const auth = useAuthStore()
const loading = ref(true)
const error = ref('')
const pageImg = ref('')
const pdfBlobUrl = ref('')
const page = ref(props.initialPage || 1)
const scale = ref(1)
const showBoxes = ref(true)
const stageRef = ref(null)
const pageWrapRef = ref(null)
const pageSize = ref({ width: 612, height: 792 })
const displayWidth = ref(640)
const displayHeight = ref(880)

let token = 0
let objectUrls = []

const paperId = computed(() => {
  if (props.paperId) return Number(props.paperId)
  const m = String(props.fileUrl || '').match(/\/papers\/(\d+)\//)
  return m ? Number(m[1]) : null
})

const thumbs = computed(() => {
  const pages = props.layoutMeta?.pages || []
  return pages.map(p => ({
    page: p.page,
    url: mediaSrc(p.preview || p.thumb),
  }))
})

const pageCount = computed(() => {
  const n = props.layoutMeta?.page_count || (props.layoutMeta?.pages || []).length
  return n || 1
})

const currentMeta = computed(() =>
  (props.layoutMeta?.pages || []).find(p => Number(p.page) === Number(page.value)) || null,
)

const pageOverlays = computed(() => {
  if (!props.interactive) return []
  const pw = pageSize.value.width || 1
  const ph = pageSize.value.height || 1
  const sx = displayWidth.value / pw
  const sy = displayHeight.value / ph
  return props.blocks
    .map((para, index) => ({ para, index }))
    .filter(x => Number(x.para.page || 0) === Number(page.value))
    .filter(x => Array.isArray(x.para.bbox) && x.para.bbox.length >= 4)
    .map(({ para, index }) => {
      const [x0, y0, x1, y1] = para.bbox.map(Number)
      const left = Math.min(x0, x1) * sx
      const top = Math.min(y0, y1) * sy
      const width = Math.abs(x1 - x0) * sx
      const height = Math.abs(y1 - y0) * sy
      if (width < 2 || height < 2) return null
      if (width > displayWidth.value * 0.98 && height > displayHeight.value * 0.55) return null
      return {
        index,
        type: para.type || 'text',
        title: (para.en || '').slice(0, 80),
        style: {
          left: `${left}px`,
          top: `${top}px`,
          width: `${width}px`,
          height: `${height}px`,
        },
      }
    })
    .filter(Boolean)
})

function mediaSrc(rel) {
  if (!rel) return ''
  if (rel.startsWith('/media') || rel.startsWith('http') || rel.startsWith('blob:')) return rel
  return `/media/${rel}`
}

function rememberUrl(url) {
  if (url && url.startsWith('blob:')) objectUrls.push(url)
  return url
}

function zoomIn() { scale.value = Math.min(2.2, +(scale.value + 0.12).toFixed(2)) }
function zoomOut() { scale.value = Math.max(0.5, +(scale.value - 0.12).toFixed(2)) }

function applySize() {
  const meta = currentMeta.value
  pageSize.value = {
    width: meta?.width || pageSize.value.width || 612,
    height: meta?.height || pageSize.value.height || 792,
  }
  const stage = stageRef.value
  const avail = stage ? Math.max(240, stage.clientWidth - 28) : 640
  displayWidth.value = Math.round(avail * scale.value)
  const ratio = (pageSize.value.height || 792) / (pageSize.value.width || 612)
  displayHeight.value = Math.round(displayWidth.value * ratio)
  emitMetrics()
}

function fitWidth() {
  scale.value = 1
  applySize()
}

function emitMetrics() {
  emit('metrics', {
    page: page.value,
    pageWidth: pageSize.value.width,
    pageHeight: pageSize.value.height,
    displayWidth: displayWidth.value,
    displayHeight: displayHeight.value,
  })
}

function goPage(p) {
  const n = Math.min(Math.max(1, Number(p) || 1), pageCount.value || 1)
  if (n !== page.value) page.value = n
}

function onOverlayClick(b) {
  emit('select-block', b.index)
}

function showInstantPreview() {
  const meta = currentMeta.value
  const src = mediaSrc(meta?.preview || meta?.thumb)
  if (src) {
    pageImg.value = src
    applySize()
    return true
  }
  return false
}

async function loadHiRes() {
  const id = paperId.value
  if (!id) return
  const t = ++token
  loading.value = true
  error.value = ''
  try {
    applySize()
    const dpr = Math.min(window.devicePixelRatio || 1, 2.5)
    const pdfW = pageSize.value.width || 612
    const need = (displayWidth.value * dpr) / Math.max(pdfW, 1)
    const zoom = Math.min(4.5, Math.max(2.2, +(need * 1.15).toFixed(2)))
    const res = await fetch(`/api/papers/${id}/page-image/?page=${page.value}&scale=${zoom}`, {
      headers: { Authorization: `Bearer ${auth.access}` },
    })
    if (!res.ok) throw new Error(`页面图 ${res.status}`)
    const blob = await res.blob()
    if (t !== token) return
    const url = rememberUrl(URL.createObjectURL(blob))
    pageImg.value = url
    applySize()
    emit('ready', { pages: pageCount.value })
  } catch (e) {
    if (!pageImg.value) error.value = e.message || String(e)
  } finally {
    if (t === token) loading.value = false
  }
}

async function ensurePdfBlob() {
  if (pdfBlobUrl.value || !props.fileUrl) return
  try {
    const res = await fetch(props.fileUrl, {
      headers: { Authorization: `Bearer ${auth.access}` },
    })
    if (!res.ok) return
    pdfBlobUrl.value = rememberUrl(URL.createObjectURL(await res.blob()))
  } catch { /* ignore */ }
}

function highlightBlock(index) {
  const para = props.blocks[index]
  if (!para) return
  if (para.page && Number(para.page) !== Number(page.value)) page.value = Number(para.page)
  nextTick(() => {
    const el = pageWrapRef.value?.querySelector('.bbox.active')
    el?.scrollIntoView?.({ block: 'center', behavior: 'smooth' })
  })
}

watch(page, (p) => {
  emit('page-change', p)
  showInstantPreview()
  loadHiRes()
})
watch(scale, () => applySize())
watch(() => props.fileUrl, () => {
  pdfBlobUrl.value = ''
  showInstantPreview()
  loadHiRes()
  ensurePdfBlob()
})
watch(() => props.layoutMeta, () => {
  showInstantPreview()
}, { deep: true })
watch(() => props.activeIndex, () => highlightBlock(props.activeIndex))
watch(() => props.initialPage, (p) => { if (p && p !== page.value) page.value = p })

onMounted(() => {
  showInstantPreview()
  applySize()
  loadHiRes()
  ensurePdfBlob()
})
onBeforeUnmount(() => {
  objectUrls.forEach((u) => URL.revokeObjectURL(u))
})

defineExpose({ page, goPage, highlightBlock, fitWidth, pageSize, displayWidth, displayHeight })
</script>

<style scoped>
.pdf-viewer {
  display: grid;
  grid-template-columns: 1fr 88px;
  grid-template-rows: auto 1fr;
  height: 100%;
  min-height: 480px;
  background: #525659;
  border-radius: 10px;
  overflow: hidden;
}
.pdf-viewer.no-thumbs { grid-template-columns: 1fr; }
.pdf-bar {
  grid-column: 1 / -1;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 8px 12px; background: #fff; border-bottom: 1px solid var(--border);
}
.pg { font-size: 13px; color: var(--text-2); min-width: 64px; text-align: center; }
.open-raw { margin-left: auto; font-size: 12.5px; }
.err { color: var(--danger); font-size: 12.5px; }
.pdf-stage {
  overflow: auto;
  position: relative;
  min-height: 0;
  padding: 16px 12px 28px;
}
.page-wrap {
  position: relative;
  margin: 0 auto;
  background: #fff;
  box-shadow: 0 4px 18px rgba(0,0,0,.28);
}
.page-img {
  display: block;
  width: 100%;
  height: auto;
  user-select: none;
  image-rendering: auto;
}
.overlay-layer {
  position: absolute; inset: 0;
  pointer-events: none;
}
.bbox {
  position: absolute;
  pointer-events: auto;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  padding: 0;
  box-sizing: border-box;
}
.bbox:hover {
  background: rgba(37, 99, 235, 0.10);
  border-color: rgba(37, 99, 235, 0.55);
}
.bbox.active {
  background: rgba(37, 99, 235, 0.16);
  border-color: #2563eb;
  z-index: 2;
}
.thumbs {
  overflow-y: auto; background: #3a3d42; border-left: 1px solid #2a2d31;
  padding: 8px 6px;
}
.thumb {
  margin-bottom: 8px; border: 2px solid transparent; border-radius: 4px;
  cursor: pointer; overflow: hidden; background: #fff; text-align: center;
  font-size: 12px; color: #cbd5e1; min-height: 40px;
}
.thumb.active { border-color: #60a5fa; }
.thumb img { width: 100%; display: block; }
.hint { padding: 48px; text-align: center; color: #e5e7eb; }
</style>
