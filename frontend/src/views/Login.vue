<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">AI</div>
        <h2>AI 中台管理系统</h2>
        <p class="subtitle">请使用管理员账号登录</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @keyup.enter="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            prefix-icon="User"
            placeholder="请输入用户名"
            size="large"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            prefix-icon="Lock"
            placeholder="请输入密码"
            show-password
            size="large"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          style="width: 100%; margin-top: 8px"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>

      <p class="login-hint">默认账号：admin / admin123</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(160deg, #f0f6ff 0%, #fafbff 60%, #f4f8f0 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  background: #fff;
  border-radius: 16px;
  padding: 48px 40px 36px;
  width: 400px;
  box-shadow: 0 4px 24px rgba(64, 158, 255, 0.08), 0 1px 4px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(64, 158, 255, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, #60b8ff, #4096e0);
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.login-header h2 {
  font-size: 20px;
  color: #1d2b3a;
  margin: 0 0 6px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.subtitle {
  color: #a8b2c0;
  font-size: 13px;
  margin: 0;
}

.login-hint {
  text-align: center;
  color: #c8cfd8;
  font-size: 12px;
  margin-top: 20px;
  margin-bottom: 0;
}
</style>
