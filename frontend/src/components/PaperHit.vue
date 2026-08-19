<template>
  <article class="paper-hit-card">
    <div class="card-top">
      <div v-if="rank" class="rank" :class="'r' + Math.min(rank, 3)">{{ rank }}</div>
      <div class="card-main">
        <div class="chips">
          <span v-if="p.reason" class="chip reason">{{ p.reason }}</span>
          <span v-if="inLib" class="chip in">已入库</span>
          <span v-else class="chip src">{{ p.venue || p.source || '检索' }}</span>
          <span v-if="p.year" class="chip">{{ p.year }}</span>
          <span v-if="p.category" class="chip">{{ p.category }}</span>
          <span v-if="p.cites" class="chip cite">被引 {{ formatCites(p.cites) }}</span>
        </div>
        <h3 class="title" @click="$emit('open', p)">{{ p.title }}</h3>
        <div v-if="p.title_zh" class="title-zh">{{ p.title_zh }}</div>
        <div class="authors">{{ p.authors || '未知作者' }}</div>
      </div>
    </div>

    <div
      v-if="absText"
      class="abs"
      :class="{ open: expanded, clickable: canExpand }"
      @click.stop="toggleAbs"
    >
      <p>{{ expanded || !canExpand ? absText : shortAbs }}</p>
      <button v-if="canExpand" type="button" class="abs-toggle">
        {{ expanded ? '收起摘要' : '展开摘要' }}
      </button>
    </div>
    <div v-else class="abs muted">暂无摘要</div>

    <div class="card-foot">
      <span v-if="p.arxiv_id" class="id">{{ p.arxiv_id }}</span>
      <span class="grow"></span>
      <el-button v-if="inLib" size="small" type="primary" round @click.stop="$emit('read', p)">阅读</el-button>
      <el-button v-else size="small" type="primary" round :loading="busy" @click.stop="$emit('import', p)">导入文献库</el-button>
    </div>
  </article>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  p: { type: Object, required: true },
  busyId: { default: '' },
  rank: { type: [Number, String], default: 0 },
})
defineEmits(['import', 'read', 'open'])

const expanded = ref(false)
const LIMIT = 160

const inLib = computed(() => !!(props.p.in_library || props.p.paper_id))
const busy = computed(() => {
  if (!props.busyId) return false
  const keys = [props.p.arxiv_id, props.p.doi, props.p.external_id, props.p.id, props.p.title]
  return keys.filter(Boolean).includes(props.busyId)
})
const absText = computed(() => String(props.p.abstract || props.p.intro || '').replace(/\s+/g, ' ').trim())
const canExpand = computed(() => absText.value.length > LIMIT)
const shortAbs = computed(() => {
  const t = absText.value
  if (t.length <= LIMIT) return t
  return `${t.slice(0, LIMIT).replace(/\s+\S*$/, '')}…`
})

watch(() => props.p.arxiv_id || props.p.id, () => { expanded.value = false })

function toggleAbs() {
  if (!canExpand.value) return
  expanded.value = !expanded.value
}

function formatCites(n) {
  const x = Number(n) || 0
  if (x >= 10000) return `${(x / 10000).toFixed(1)}万`
  if (x >= 1000) return x.toLocaleString()
  return String(x)
}
</script>

<style scoped>
.paper-hit-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 20px 14px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
  transition: box-shadow .18s ease, border-color .18s ease, transform .18s ease;
  position: relative;
  overflow: hidden;
}
.paper-hit-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, var(--primary), #8b5cf6);
  opacity: .85;
}
.paper-hit-card:hover {
  border-color: #c7d7fe;
  box-shadow: 0 10px 28px rgba(37, 99, 235, 0.1);
  transform: translateY(-1px);
}
.card-top { display: flex; gap: 12px; align-items: flex-start; }
.rank {
  flex: none;
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 15px;
  color: var(--text-3);
  background: #f3f4f6;
  margin-top: 2px;
}
.rank.r1 { color: #fff; background: linear-gradient(135deg, #ef4444, #f97316); }
.rank.r2 { color: #fff; background: linear-gradient(135deg, #f59e0b, #f97316); }
.rank.r3 { color: #fff; background: linear-gradient(135deg, #eab308, #f59e0b); }
.card-main { flex: 1; min-width: 0; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.chip {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f3f4f6;
  color: var(--text-2);
}
.chip.reason { background: var(--primary-light); color: var(--primary); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip.in { background: #ecfdf5; color: #059669; }
.chip.src { background: #eef2ff; color: #4f46e5; }
.chip.cite { background: #fff7ed; color: #c2410c; font-weight: 650; }
.title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.4;
  color: #111827;
  cursor: pointer;
}
.title:hover { color: var(--primary); }
.title-zh { margin-top: 4px; font-size: 13px; color: var(--text-2); }
.authors {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.abs {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px dashed #e2e8f0;
}
.abs p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.75;
  color: #334155;
}
.abs.clickable { cursor: pointer; }
.abs.clickable:hover { border-color: #93c5fd; background: #f8fbff; }
.abs-toggle {
  display: inline-block;
  margin-top: 8px;
  border: 0;
  background: none;
  padding: 0;
  color: var(--primary);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.card-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
.id { font-size: 12px; color: var(--text-3); font-family: ui-monospace, Consolas, monospace; }
.grow { flex: 1; }
.muted { color: var(--text-3); font-size: 13px; padding: 12px 0 0; }
</style>
