<template>
  <div class="admin">
    <el-tabs v-model="tab" @tab-change="onTab">
      <el-tab-pane label="用户管理" name="users" />
      <el-tab-pane label="会员套餐" name="plans" />
      <el-tab-pane label="支付订单" name="orders" />
    </el-tabs>

    <div v-show="tab==='users'">
      <div class="toolbar">
        <el-input v-model="q" placeholder="搜索昵称 / 邮箱" clearable style="width:240px" @keyup.enter="loadUsers" />
        <el-select v-model="statusFilter" clearable placeholder="状态" style="width:120px" @change="loadUsers">
          <el-option label="正常" :value="1" />
          <el-option label="停用" :value="0" />
        </el-select>
        <el-button type="primary" @click="loadUsers">查询</el-button>
      </div>
      <el-table :data="users" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="昵称" min-width="110" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="role" label="角色" width="110" />
        <el-table-column label="会员" min-width="140">
          <template #default="{ row }">{{ row.membership?.plan_name || '未开通' }}</template>
        </el-table-column>
        <el-table-column label="每日翻译/解析" width="130">
          <template #default="{ row }">
            {{ quotaText(row, 'daily_translate') }} / {{ quotaText(row, 'daily_parse') }}
          </template>
        </el-table-column>
        <el-table-column label="页数" width="70">
          <template #default="{ row }">{{ quotaText(row, 'page_limit') }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status===1 ? 'success' : 'info'" size="small">{{ row.status===1 ? '正常' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="editUser(row)">编辑</el-button>
            <el-button text type="warning" @click="openReset(row)">重置密码</el-button>
            <el-button text type="danger" @click="removeUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        class="pager"
        layout="total, prev, pager, next"
        :total="userTotal"
        v-model:current-page="userPage"
        :page-size="10"
        @current-change="loadUsers"
      />
    </div>

    <div v-show="tab==='plans'">
      <p class="muted tip">修改后立即对未单独覆盖配额的用户生效。团队共享填 -1 表示不限，0 表示不可共享。</p>
      <el-table :data="plans" stripe>
        <el-table-column prop="name" label="套餐" width="120" />
        <el-table-column label="每日翻译">
          <template #default="{ row }"><el-input-number v-model="row.daily_translate" :min="0" :max="999" /></template>
        </el-table-column>
        <el-table-column label="每日解析">
          <template #default="{ row }"><el-input-number v-model="row.daily_parse" :min="0" :max="999" /></template>
        </el-table-column>
        <el-table-column label="页数上限">
          <template #default="{ row }"><el-input-number v-model="row.page_limit" :min="1" :max="999" /></template>
        </el-table-column>
        <el-table-column label="月费（元）">
          <template #default="{ row }"><el-input-number v-model="row.price_month" :min="0" :precision="2" :step="1" /></template>
        </el-table-column>
        <el-table-column label="团队共享">
          <template #default="{ row }"><el-input-number v-model="row.team_share_limit" :min="-1" :max="9999" /></template>
        </el-table-column>
        <el-table-column label="可购买" width="90">
          <template #default="{ row }"><el-switch v-model="row.purchasable" /></template>
        </el-table-column>
        <el-table-column label="" width="90">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="savePlan(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-show="tab==='orders'">
      <div class="toolbar">
        <el-select v-model="orderStatus" clearable placeholder="订单状态" style="width:140px" @change="loadOrders">
          <el-option label="待支付" value="pending" />
          <el-option label="已支付" value="paid" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
        <el-button type="primary" @click="loadOrders">刷新</el-button>
      </div>
      <el-table :data="orders" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户" min-width="110" />
        <el-table-column prop="plan_name" label="套餐" width="110" />
        <el-table-column label="金额" width="90">
          <template #default="{ row }">¥{{ Number(row.amount).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="渠道" width="100">
          <template #default="{ row }">{{ row.channel === 'wechat' ? '微信' : '支付宝' }}</template>
        </el-table-column>
        <el-table-column prop="trade_no" label="订单号" min-width="180" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status==='paid' ? 'success' : (row.status==='pending' ? 'warning' : 'info')" size="small">
              {{ { pending: '待支付', paid: '已支付', cancelled: '已取消' }[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="支付时间" min-width="160">
          <template #default="{ row }">{{ row.paid_at ? new Date(row.paid_at).toLocaleString() : '—' }}</template>
        </el-table-column>
        <el-table-column label="下单时间" min-width="160">
          <template #default="{ row }">{{ row.created_at ? new Date(row.created_at).toLocaleString() : '—' }}</template>
        </el-table-column>
      </el-table>
      <el-pagination
        class="pager"
        layout="total, prev, pager, next"
        :total="orderTotal"
        v-model:current-page="orderPage"
        :page-size="10"
        @current-change="loadOrders"
      />
    </div>

    <el-dialog v-model="userVisible" title="编辑用户" width="560px" destroy-on-close>
      <el-form v-if="editing" label-width="120px">
        <el-form-item label="昵称"><el-input v-model="editing.username" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="editing.email" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editing.role" style="width:100%">
            <el-option label="普通用户" value="普通用户" />
            <el-option label="技术负责人" value="技术负责人" />
            <el-option label="团队管理员" value="团队管理员" />
            <el-option label="专业版" value="专业版" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editing.status" style="width:100%">
            <el-option label="正常" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item label="管理员权限"><el-switch v-model="editing.is_staff" /></el-form-item>
        <el-form-item label="会员套餐">
          <el-select v-model="editing.membership_plan" clearable placeholder="未开通" style="width:100%">
            <el-option v-for="p in plans" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="到期时间">
          <el-date-picker v-model="editing.membership_expire_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="留空表示长期有效" style="width:100%" />
        </el-form-item>
        <p class="muted tip">下面四项留空则跟随套餐；填写后只对该用户生效。</p>
        <el-form-item label="每日翻译篇数"><el-input v-model="editing.quota_translate_daily" placeholder="跟随套餐" /></el-form-item>
        <el-form-item label="每日解析篇数"><el-input v-model="editing.quota_parse_daily" placeholder="跟随套餐" /></el-form-item>
        <el-form-item label="论文页数上限"><el-input v-model="editing.quota_page_limit" placeholder="跟随套餐" /></el-form-item>
        <el-form-item label="团队共享次数"><el-input v-model="editing.quota_team_share" placeholder="跟随套餐，-1 不限" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetVisible" :title="resetTitle" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="新密码（至少 8 位）">
          <el-input v-model="resetForm.password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="resetForm.password2" type="password" show-password autocomplete="new-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fillRandomPassword">随机生成</el-button>
        <el-button @click="resetVisible=false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="submitReset">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api/http'

const route = useRoute()
const router = useRouter()
const tab = ref('users')
const q = ref('')
const statusFilter = ref(null)
const users = ref([])
const userTotal = ref(0)
const userPage = ref(1)
const plans = ref([])
const userVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const resetVisible = ref(false)
const resetting = ref(false)
const resetUser = ref(null)
const resetForm = ref({ password: '', password2: '' })
const resetTitle = computed(() => resetUser.value ? `重置「${resetUser.value.username}」的密码` : '重置密码')
const orders = ref([])
const orderTotal = ref(0)
const orderPage = ref(1)
const orderStatus = ref('')

function quotaText(row, key) {
  const m = row.membership || {}
  if (m.unlimited) return '不限'
  const v = m[key]
  return v == null ? '—' : v
}

async function loadUsers() {
  const data = await api.get('/auth/admin/users/', {
    params: { q: q.value, status: statusFilter.value, page: userPage.value, page_size: 10 },
  })
  users.value = data.results || []
  userTotal.value = data.count || 0
}

async function loadPlans() {
  plans.value = (await api.get('/auth/admin/plans/') || []).map((p) => ({
    ...p,
    price_month: Number(p.price_month),
  }))
}

function editUser(row) {
  editing.value = {
    ...row,
    quota_translate_daily: row.quota_translate_daily ?? '',
    quota_parse_daily: row.quota_parse_daily ?? '',
    quota_page_limit: row.quota_page_limit ?? '',
    quota_team_share: row.quota_team_share ?? '',
    membership_expire_at: row.membership_expire_at ? String(row.membership_expire_at).slice(0, 19) : '',
  }
  userVisible.value = true
}

function toIntOrNull(v) {
  if (v === '' || v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

async function saveUser() {
  const e = editing.value
  if (!e) return
  saving.value = true
  try {
    await api.patch(`/auth/admin/users/${e.id}/`, {
      username: e.username,
      email: e.email,
      role: e.role,
      status: e.status,
      is_staff: e.is_staff,
      membership_plan: e.membership_plan || null,
      membership_expire_at: e.membership_expire_at || null,
      quota_translate_daily: toIntOrNull(e.quota_translate_daily),
      quota_parse_daily: toIntOrNull(e.quota_parse_daily),
      quota_page_limit: toIntOrNull(e.quota_page_limit),
      quota_team_share: toIntOrNull(e.quota_team_share),
    })
    ElMessage.success('已保存')
    userVisible.value = false
    await loadUsers()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function openReset(row) {
  resetUser.value = row
  resetForm.value = { password: '', password2: '' }
  resetVisible.value = true
}

function fillRandomPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  let pwd = ''
  const buf = new Uint32Array(10)
  crypto.getRandomValues(buf)
  for (let i = 0; i < 10; i++) pwd += chars[buf[i] % chars.length]
  resetForm.value = { password: pwd, password2: pwd }
}

async function submitReset() {
  const row = resetUser.value
  const { password, password2 } = resetForm.value
  if (!row) return
  if (!password || password.length < 8) {
    ElMessage.warning('新密码至少 8 位')
    return
  }
  if (password !== password2) {
    ElMessage.warning('两次密码不一致')
    return
  }
  resetting.value = true
  try {
    await api.post(`/auth/admin/users/${row.id}/reset-password/`, { password, password2 })
    ElMessage.success(`已重置「${row.username}」的密码`)
    resetVisible.value = false
  } catch (err) {
    ElMessage.error(err.message || '重置失败')
  } finally {
    resetting.value = false
  }
}

async function removeUser(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」？账号将被停用。`, '删除用户', { type: 'warning' })
    await api.delete(`/auth/admin/users/${row.id}/`)
    ElMessage.success('已删除')
    loadUsers()
  } catch (err) {
    if (err !== 'cancel' && err?.message) ElMessage.error(err.message)
  }
}

async function savePlan(row) {
  try {
    await api.patch(`/auth/admin/plans/${row.id}/`, {
      name: row.name,
      daily_translate: row.daily_translate,
      daily_parse: row.daily_parse,
      page_limit: row.page_limit,
      price_month: row.price_month,
      team_share_limit: row.team_share_limit,
      purchasable: row.purchasable,
    })
    ElMessage.success(`${row.name} 已更新`)
    await loadPlans()
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  }
}

async function loadOrders() {
  const data = await api.get('/auth/admin/orders/', {
    params: { status: orderStatus.value, page: orderPage.value, page_size: 10 },
  })
  orders.value = data.results || []
  orderTotal.value = data.count || 0
}

function onTab(name) {
  router.replace({ query: { ...route.query, tab: name } })
  if (name === 'orders') {
    orderPage.value = 1
    loadOrders()
  }
}

watch(
  () => route.query.tab,
  (v) => {
    if (v === 'orders' || v === 'plans' || v === 'users') tab.value = v
  },
  { immediate: true },
)

onMounted(async () => {
  await loadPlans()
  await loadUsers()
  if (tab.value === 'orders') await loadOrders()
})
</script>

<style scoped>
.admin { padding: 12px 20px 28px; }
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.pager { margin-top: 12px; justify-content: flex-end; }
.tip { margin: 0 0 12px; font-size: 13px; }
</style>
