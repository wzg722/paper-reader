<template>
  <div class="auth-page">
    <div class="auth-card card">
      <div class="brand"><span class="mark">P</span><h1>PaperMind</h1></div>
      <p class="muted">登录论文精读平台</p>
      <el-form :model="form" @submit.prevent="onSubmit" label-position="top">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="demo@papermind.local" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="demo123456" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">登录</el-button>
        <el-button style="width:100%;margin-top:10px;margin-left:0" @click="demoLogin">演示账号一键登录</el-button>
      </el-form>
      <p class="foot">还没有账号？<router-link to="/register">注册</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = reactive({ email: '', password: '' })

function nextPath() {
  const raw = route.query.redirect
  if (typeof raw !== 'string') return '/'
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/login') || raw.startsWith('/register')) {
    return '/'
  }
  return raw
}

async function onSubmit() {
  loading.value = true
  try {
    await auth.login(form.email, form.password)
    ElMessage.success('登录成功')
    router.replace(nextPath())
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function demoLogin() {
  form.email = 'demo@papermind.local'
  form.password = 'demo123456'
  await onSubmit()
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(160deg, #eff6ff 0%, #f5f7fb 40%, #faf5ff 100%);
}
.auth-card { width: 400px; padding: 32px; }
.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.brand h1 { font-size: 22px; }
.mark {
  width: 36px; height: 36px; border-radius: 10px;
  background: linear-gradient(135deg, var(--primary), var(--purple));
  color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800;
}
.foot { margin-top: 16px; text-align: center; color: var(--text-2); }
</style>
