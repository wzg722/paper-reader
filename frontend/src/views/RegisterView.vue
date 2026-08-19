<template>
  <div class="auth-page">
    <div class="auth-card card">
      <div class="brand"><span class="mark">P</span><h1>注册 PaperMind</h1></div>
      <el-form :model="form" @submit.prevent="onSubmit" label-position="top">
        <el-form-item label="姓名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="身份证号（可选）"><el-input v-model="form.id_card" maxlength="18" /></el-form-item>
        <el-form-item label="密码（≥8位）"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="确认密码"><el-input v-model="form.password2" type="password" show-password /></el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">注册</el-button>
      </el-form>
      <p class="foot">已有账号？<router-link to="/login">登录</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', email: '', id_card: '', password: '', password2: '' })

async function onSubmit() {
  loading.value = true
  try {
    await auth.register(form)
    ElMessage.success('注册成功，已预置 6 个收藏网站')
    router.replace('/')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(160deg, #eff6ff 0%, #f5f7fb 40%, #faf5ff 100%);
}
.auth-card { width: 420px; padding: 32px; }
.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.brand h1 { font-size: 20px; }
.mark {
  width: 36px; height: 36px; border-radius: 10px;
  background: linear-gradient(135deg, var(--primary), var(--purple));
  color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800;
}
.foot { margin-top: 16px; text-align: center; color: var(--text-2); }
</style>
