<template>
  <div class="container">
    <div class="card pad profile">
      <div class="av">{{ auth.user?.avatar }}</div>
      <div>
        <h2>{{ auth.user?.username }}</h2>
        <p class="muted">{{ auth.user?.email }} · {{ auth.user?.role }}</p>
        <p>身份证：{{ auth.user?.id_card_masked || '未填写' }}</p>
        <p>研究方向：{{ auth.user?.research_direction || '未设置' }}</p>
        <el-button size="small" @click="editVisible=true">📝 修改资料</el-button>
      </div>
    </div>

    <div class="card pad membership-box">
      <div class="ms-head">
        <div>
          <h3>{{ ms.plan_name || '未开通会员' }}</h3>
          <p class="muted">{{ expireText }}</p>
        </div>
        <div class="ms-quota" v-if="ms.unlimited">管理员 · 翻译/解析不限</div>
        <div class="ms-quota" v-else>
          今日翻译 {{ ms.translate_used || 0 }}/{{ ms.daily_translate }} ·
          解析 {{ ms.parse_used || 0 }}/{{ ms.daily_parse }} ·
          页数 ≤ {{ ms.page_limit }} ·
          团队共享 {{ shareText }}
        </div>
      </div>
      <div class="plan-grid">
        <article v-for="p in plans" :key="p.id" class="plan" :class="{on: ms.plan_id===p.id}">
          <div class="plan-name">{{ p.name }}</div>
          <div class="plan-price">
            <b>{{ Number(p.price_month) === 0 ? '免费' : `¥${Number(p.price_month)}` }}</b>
            <span v-if="Number(p.price_month) > 0"> / 月</span>
          </div>
          <ul>
            <li>每天翻译 {{ p.daily_translate }} 篇</li>
            <li>每天版面解析 {{ p.daily_parse }} 篇</li>
            <li>论文不超过 {{ p.page_limit }} 页</li>
            <li>{{ shareLabel(p.team_share_limit) }}</li>
          </ul>
          <el-button
            type="primary"
            size="small"
            :disabled="ms.unlimited || (ms.plan_id===p.id && !expired)"
            :loading="buying===p.id"
            @click="buy(p)"
          >{{ ms.plan_id===p.id && !expired ? '当前套餐' : (Number(p.price_month)===0 ? '开通' : '去支付') }}</el-button>
        </article>
      </div>
    </div>

    <div class="stats">
      <div class="card pad" v-for="(v,k) in statsShow" :key="k"><div class="num">{{ v }}</div><div class="muted">{{ k }}</div></div>
    </div>

    <div class="section-title">已加入团队</div>
    <div class="team-row">
      <div v-for="t in teams" :key="t.id" class="card pad team" @click="$router.push('/community')">
        {{ t.avatar }} {{ t.name }}
        <el-tag v-if="t.is_owner" size="small" type="warning">队长</el-tag>
      </div>
      <div v-if="!teams.length" class="muted">尚未加入团队，去社区看看吧</div>
    </div>

    <div class="section-title">偏好设置</div>
    <div class="card pad">
      <h4>翻译引擎（DeepSeek）</h4>
      <el-form label-width="100px" style="max-width:560px">
        <el-form-item label="接口地址"><el-input v-model="pref.translate_config.url" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="pref.translate_config.api_key" type="password" show-password /></el-form-item>
        <el-form-item label="模型"><el-input v-model="pref.translate_config.model" placeholder="deepseek-chat / deepseek-v4" /></el-form-item>
        <el-button @click="savePref">保存</el-button>
        <el-button @click="testEngine('translate')" :loading="testingT">🔌 测试连接</el-button>
        <span v-if="testT" class="muted" style="margin-left:8px">{{ testT }}</span>
      </el-form>

      <h4 style="margin-top:20px">OCR / 版面解析</h4>
      <el-form label-width="100px" style="max-width:560px">
        <el-form-item label="服务地址"><el-input v-model="pref.ocr_config.url" :placeholder="pref.ocr_config.provider==='mineru' ? 'http://127.0.0.1:8001' : 'http://127.0.0.1:8866'" /></el-form-item>
        <el-form-item label="Provider">
          <el-select v-model="pref.ocr_config.provider" style="width:200px">
            <el-option label="PaddleOCR" value="paddleocr" />
            <el-option label="MinerU" value="mineru" />
          </el-select>
        </el-form-item>
        <p class="muted" style="margin:-4px 0 10px">导入选 MinerU 时，会请求 MINERU_API_URL（默认 :8001）。个人中心选 MinerU 时，截图 OCR 也走该地址。</p>
        <el-button @click="savePref">保存</el-button>
        <el-button @click="testEngine('ocr')" :loading="testingO">🔌 测试连接</el-button>
        <span v-if="testO" class="muted" style="margin-left:8px">{{ testO }}</span>
      </el-form>
    </div>

    <div class="section-title">数据备份</div>
    <div class="card pad">
      <el-button type="primary" @click="exportBackup">⬇ 导出备份 JSON</el-button>
    </div>

    <el-dialog
      v-model="payVisible"
      :title="payTitle"
      width="420px"
      :close-on-click-modal="false"
      @closed="onPayClosed"
    >
      <div v-if="payPlan" class="pay-box">
        <div class="pay-amount">¥{{ Number(payPlan.price_month).toFixed(2) }}<span> / 月</span></div>
        <p class="muted">开通「{{ payPlan.name }}」1 个月</p>
        <el-radio-group v-model="payChannel" :disabled="!!payOrder" class="pay-channels">
          <el-radio-button value="alipay">支付宝</el-radio-button>
          <el-radio-button value="wechat">微信支付</el-radio-button>
        </el-radio-group>
        <div v-if="payQr" class="pay-qr">
          <img :src="payQrUrl" alt="支付二维码" width="180" height="180" />
          <p class="muted">请使用{{ payChannel === 'wechat' ? '微信' : '支付宝' }}扫码支付</p>
          <p class="trade">订单号 {{ payOrder?.trade_no }}</p>
          <p class="muted">支付完成后点击「我已完成支付」，会员将自动升级并通知管理员。</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="cancelPay">取消</el-button>
        <el-button v-if="!payOrder" type="primary" :loading="buying===payPlan?.id" @click="createPayOrder">去支付</el-button>
        <el-button v-else type="primary" :loading="confirming" @click="confirmPay">我已完成支付</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="修改资料" width="420px">
      <el-form label-position="top">
        <el-form-item label="昵称"><el-input v-model="editForm.username" /></el-form-item>
        <el-form-item label="头像（emoji）"><el-input v-model="editForm.avatar" /></el-form-item>
        <el-form-item label="身份证"><el-input v-model="editForm.id_card" maxlength="18" /></el-form-item>
        <el-form-item label="研究方向"><el-input v-model="editForm.research_direction" placeholder="顿号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible=false">取消</el-button>
        <el-button type="primary" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/http'

const auth = useAuthStore()
const stats = ref({})
const teams = ref([])
const editVisible = ref(false)
const editForm = reactive({ username: '', avatar: '', id_card: '', research_direction: '' })
const pref = reactive({
  translate_config: {
    provider: 'newapi',
    _type: 'newapi_channel_conn',
    url: 'https://llm.talkweb.com.cn',
    api_key: '',
    model: 'deepseek-v4-flash',
    timeout: 60,
  },
  ocr_config: { url: 'http://127.0.0.1:8866', provider: 'paddleocr', timeout: 30 },
  lang: 'zh',
})
const testingT = ref(false)
const testingO = ref(false)
const testT = ref('')
const testO = ref('')
const plans = ref([])
const buying = ref(null)
const payVisible = ref(false)
const payPlan = ref(null)
const payChannel = ref('alipay')
const payOrder = ref(null)
const payQr = ref('')
const confirming = ref(false)
const skipCancel = ref(false)

const payTitle = computed(() => payPlan.value ? `支付开通「${payPlan.value.name}」` : '支付')
const payQrUrl = computed(() => {
  if (!payQr.value) return ''
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(payQr.value)}`
})

const ms = computed(() => auth.user?.membership || {})
const expired = computed(() => {
  const exp = ms.value.expire_at
  if (!exp) return false
  return new Date(exp).getTime() < Date.now()
})
const expireText = computed(() => {
  if (ms.value.unlimited) return '管理员账号，翻译与版面解析不受限制'
  if (!ms.value.expire_at) {
    return ms.value.plan_code === 'free' || !ms.value.plan_id ? '未开通付费会员' : '长期有效'
  }
  return `有效期至 ${new Date(ms.value.expire_at).toLocaleString()}`
})
const shareText = computed(() => {
  const n = ms.value.team_share_limit
  if (n < 0) return '不限'
  if (!n) return '不可用'
  return `${ms.value.team_share_used || 0}/${n}（本月）`
})

function shareLabel(n) {
  if (n < 0) return '团队共享不限次数'
  if (!n) return '无法团队共享'
  return `每月可团队共享 ${n} 次`
}

const statsShow = computed(() => ({
  '论文': stats.value.paper_count || 0,
  '读完': stats.value.read_done || 0,
  '笔记': stats.value.note_count || 0,
  '高亮': stats.value.highlight_count || 0,
  '精读(分)': Math.round((stats.value.duration_sec || 0) / 60),
}))

async function load() {
  await auth.fetchMe()
  stats.value = await api.get('/auth/stats/')
  teams.value = await api.get('/teams/mine/')
  const p = await api.get('/auth/preference/')
  Object.assign(pref, p)
  pref.translate_config = p.translate_config || pref.translate_config
  pref.ocr_config = p.ocr_config || pref.ocr_config
  try { plans.value = await api.get('/auth/membership/plans/') || [] } catch { plans.value = [] }
  Object.assign(editForm, {
    username: auth.user.username,
    avatar: auth.user.avatar,
    research_direction: auth.user.research_direction || '',
  })
}

async function saveProfile() {
  await auth.updateMe(editForm)
  ElMessage.success('已保存')
  editVisible.value = false
}

async function savePref() {
  await api.put('/auth/preference/', pref)
  ElMessage.success('偏好已保存')
}

async function testEngine(engine) {
  if (engine === 'translate') {
    testingT.value = true
    try {
      const r = await api.post('/ai/test-engine/', { engine: 'translate', config: pref.translate_config })
      testT.value = r.ok ? `✓ 服务可达（${r.latency_ms}ms）` : `✗ ${r.error || r.status_code}`
    } finally {
      testingT.value = false
    }
  } else {
    testingO.value = true
    try {
      const r = await api.post('/ai/test-engine/', { engine: 'ocr', url: pref.ocr_config.url })
      testO.value = r.ok ? `✓ 服务可达（${r.latency_ms}ms）` : `✗ ${r.error || r.status_code}`
    } finally {
      testingO.value = false
    }
  }
}

async function exportBackup() {
  const data = await api.get('/papers/backup/')
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `papermind-backup-${Date.now()}.json`
  a.click()
  ElMessage.success('备份已下载')
}

async function buy(p) {
  const price = Number(p.price_month) || 0
  if (price > 0) {
    payPlan.value = p
    payChannel.value = 'alipay'
    payOrder.value = null
    payQr.value = ''
    skipCancel.value = false
    payVisible.value = true
    return
  }
  try {
    await ElMessageBox.confirm(`确认开通「${p.name}」？`, '开通会员', { type: 'info', confirmButtonText: '确认开通' })
  } catch {
    return
  }
  buying.value = p.id
  try {
    await api.post('/auth/membership/checkout/', { plan_id: p.id, months: 1, channel: 'alipay' })
    await auth.fetchMe()
    ElMessage.success(`已开通${p.name}`)
  } catch (e) {
    ElMessage.error(e.message || '开通失败')
  } finally {
    buying.value = null
  }
}

async function createPayOrder() {
  const p = payPlan.value
  if (!p) return
  buying.value = p.id
  try {
    const data = await api.post('/auth/membership/checkout/', {
      plan_id: p.id,
      months: 1,
      channel: payChannel.value,
    })
    if (data?.need_pay) {
      payOrder.value = data.order
      payQr.value = data.qr_svg || ''
      return
    }
    skipCancel.value = true
    payVisible.value = false
    await auth.fetchMe()
    ElMessage.success(`已开通${p.name}`)
  } catch (e) {
    ElMessage.error(e.message || '下单失败')
  } finally {
    buying.value = null
  }
}

async function confirmPay() {
  if (!payOrder.value) return
  confirming.value = true
  try {
    await api.post(`/auth/membership/orders/${payOrder.value.id}/pay/`)
    skipCancel.value = true
    payVisible.value = false
    await auth.fetchMe()
    ElMessage.success('支付成功，会员已升级')
  } catch (e) {
    ElMessage.error(e.message || '尚未确认到账，请支付后再试')
  } finally {
    confirming.value = false
  }
}

async function cancelPay() {
  payVisible.value = false
}

async function onPayClosed() {
  const order = payOrder.value
  payPlan.value = null
  payOrder.value = null
  payQr.value = ''
  if (skipCancel.value || !order || order.status !== 'pending') return
  try {
    await api.post(`/auth/membership/orders/${order.id}/cancel/`)
  } catch { /* ignore */ }
}

onMounted(load)
</script>

<style scoped>
.pad { padding: 18px; }
.profile { display: flex; gap: 18px; align-items: center; margin-bottom: 16px; }
.av {
  width: 72px; height: 72px; border-radius: 50%; font-size: 36px;
  background: linear-gradient(135deg, #60a5fa, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
}
.stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 16px; text-align: center; }
.num { font-size: 22px; font-weight: 700; color: var(--primary); }
.team-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
.team { cursor: pointer; }
.membership-box { margin-bottom: 16px; }
.ms-head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 14px; flex-wrap: wrap; }
.ms-head h3 { margin-bottom: 4px; }
.ms-quota { color: var(--text-2); font-size: 13px; }
.plan-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
.plan {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  background: #fff;
}
.plan.on { border-color: var(--primary); }
.plan-name { font-weight: 700; margin-bottom: 4px; }
.plan-price { margin-bottom: 8px; color: var(--primary); }
.plan-price span { font-size: 12px; color: var(--text-3); font-weight: 400; }
.plan ul { margin: 0 0 10px; padding-left: 16px; color: var(--text-2); font-size: 12.5px; line-height: 1.7; }
.pay-box { text-align: center; }
.pay-amount { font-size: 32px; font-weight: 700; color: var(--primary); line-height: 1.2; }
.pay-amount span { font-size: 13px; font-weight: 400; color: var(--text-3); }
.pay-channels { margin: 12px 0 8px; }
.pay-qr { margin-top: 12px; }
.pay-qr img { display: block; margin: 0 auto 8px; border: 1px solid var(--border); }
.trade { font-size: 12px; color: var(--text-3); word-break: break-all; }
@media (max-width: 1100px) { .plan-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 800px) { .stats { grid-template-columns: repeat(2, 1fr); } }
</style>
