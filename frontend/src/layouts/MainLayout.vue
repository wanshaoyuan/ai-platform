<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
      <!-- Logo 区域 -->
      <div class="logo-area">
        <el-icon v-if="isCollapsed" size="24" color="#3b82f6"><Platform /></el-icon>
        <span v-else class="logo-text">{{ settingsStore.siteTitle }}</span>
      </div>

      <!-- 导航菜单 -->
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        background-color="var(--el-bg-color)"
        text-color="var(--el-text-color-regular)"
        active-text-color="#3b82f6"
        class="side-menu"
      >
        <!-- 余额管理模块 -->
        <el-sub-menu index="income">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>余额管理</span>
          </template>
          <el-menu-item index="/income/dashboard">
            <el-icon><DataLine /></el-icon>
            <span>余额概览</span>
          </el-menu-item>
          <el-menu-item index="/income/records">
            <el-icon><List /></el-icon>
            <span>余额录入</span>
          </el-menu-item>
          <el-menu-item index="/income/accounts">
            <el-icon><Setting /></el-icon>
            <span>账户管理</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- 预留模块占位 -->
        <!-- 债务管理模块 -->
        <el-sub-menu index="debt">
          <template #title>
            <el-icon><CreditCard /></el-icon>
            <span>债务管理</span>
          </template>
          <el-menu-item index="/debt/dashboard">
            <el-icon><DataLine /></el-icon>
            <span>债务概览</span>
          </el-menu-item>
          <el-menu-item index="/debt/list">
            <el-icon><List /></el-icon>
            <span>债务列表</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>

      <!-- 折叠按钮 -->
      <div class="collapse-btn" @click="isCollapsed = !isCollapsed">
        <el-icon><DArrowLeft v-if="!isCollapsed" /><DArrowRight v-else /></el-icon>
      </div>
    </el-aside>

    <!-- 右侧主区域 -->
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="top-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentTitle">{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <!-- 主题切换 -->
          <el-tooltip :content="themeLabel" placement="bottom">
            <el-button circle text @click="cycleTheme">
              <el-icon size="18">
                <Sunny v-if="settingsStore.themeMode === 'light'" />
                <Moon v-else-if="settingsStore.themeMode === 'dark'" />
                <Monitor v-else />
              </el-icon>
            </el-button>
          </el-tooltip>

          <el-dropdown @command="handleCommand">
            <div class="user-info">
              <el-avatar size="small" :style="{ background: '#3b82f6' }">
                {{ userInitial }}
              </el-avatar>
              <span class="username">{{ authStore.user?.username }}</span>
              <el-icon class="ml-1"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="site-title">
                  <el-icon><Edit /></el-icon> 修改标题
                </el-dropdown-item>
                <el-dropdown-item command="change-password">
                  <el-icon><Lock /></el-icon> 修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 页面内容 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <!-- 修改密码弹窗 -->
  <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px" destroy-on-close>
    <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="90px">
      <el-form-item label="原密码" prop="oldPassword">
        <el-input v-model="pwdForm.oldPassword" type="password" show-password placeholder="请输入原密码" />
      </el-form-item>
      <el-form-item label="新密码" prop="newPassword">
        <el-input v-model="pwdForm.newPassword" type="password" show-password placeholder="至少 6 位" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirmPassword">
        <el-input v-model="pwdForm.confirmPassword" type="password" show-password placeholder="再次输入新密码" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="pwdDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="pwdSaving" @click="handleChangePwd">确认修改</el-button>
    </template>
  </el-dialog>

  <!-- 修改网页标题弹窗 -->
  <el-dialog v-model="titleDialogVisible" title="修改网页标题" width="380px" destroy-on-close>
    <el-form @submit.prevent>
      <el-form-item label="标题">
        <el-input
          v-model="titleInput"
          placeholder="请输入网页标题"
          maxlength="20"
          show-word-limit
          clearable
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="titleDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSaveTitle">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore, type ThemeMode } from '@/stores/settings'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { authApi } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const isCollapsed = ref(false)

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title as string | undefined)
const userInitial = computed(() =>
  (authStore.user?.username || 'U').charAt(0).toUpperCase()
)

// ---- 主题切换 ----
const themeLabels: Record<ThemeMode, string> = {
  light: '浅色模式',
  dark: '深色模式',
  system: '跟随系统',
}
const themeLabel = computed(() => themeLabels[settingsStore.themeMode])
const themeOrder: ThemeMode[] = ['light', 'dark', 'system']

function cycleTheme() {
  const idx = themeOrder.indexOf(settingsStore.themeMode)
  const next = themeOrder[(idx + 1) % themeOrder.length] ?? 'system'
  settingsStore.setTheme(next)
}

// ---- 修改标题 ----
const titleDialogVisible = ref(false)
const titleInput = ref('')

function handleSaveTitle() {
  settingsStore.setTitle(titleInput.value)
  titleDialogVisible.value = false
  ElMessage.success('标题已更新')
}

// ---- 修改密码 ----
const pwdDialogVisible = ref(false)
const pwdSaving = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })
const pwdRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (value !== pwdForm.newPassword) callback(new Error('两次密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function handleChangePwd() {
  const valid = await pwdFormRef.value?.validate().catch(() => false)
  if (!valid) return
  pwdSaving.value = true
  try {
    await authApi.changePassword(pwdForm.oldPassword, pwdForm.newPassword)
    ElMessage.success('密码修改成功，请重新登录')
    pwdDialogVisible.value = false
    authStore.logout()
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '修改失败')
  } finally {
    pwdSaving.value = false
  }
}

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    ElMessageBox.confirm('确认退出登录？', '提示', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    }).then(() => {
      authStore.logout()
      router.push('/login')
    })
  } else if (cmd === 'change-password') {
    pwdForm.oldPassword = ''
    pwdForm.newPassword = ''
    pwdForm.confirmPassword = ''
    pwdDialogVisible.value = true
  } else if (cmd === 'site-title') {
    titleInput.value = settingsStore.siteTitle
    titleDialogVisible.value = true
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  overflow: hidden;
}

/* 侧边栏 */
.sidebar {
  background: var(--el-bg-color);
  display: flex;
  flex-direction: column;
  transition: width 0.25s;
  overflow: hidden;
  border-right: 1px solid var(--el-border-color-light);
}

.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color-light);
  flex-shrink: 0;
}

.logo-text {
  color: #3b82f6;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 2px;
  white-space: nowrap;
}

.side-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 激活菜单项背景色——覆盖 Element Plus 默认的黑色 */
.side-menu :deep(.el-menu-item.is-active) {
  background-color: rgba(59, 130, 246, 0.08) !important;
  border-radius: 6px;
}
.side-menu :deep(.el-menu-item.is-active:hover) {
  background-color: rgba(59, 130, 246, 0.12) !important;
}
.side-menu :deep(.el-menu-item:hover) {
  background-color: var(--el-fill-color-light) !important;
  border-radius: 6px;
}

/* sub-menu 标题展开/激活态背景——覆盖默认黑色 */
.side-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title),
.side-menu :deep(.el-sub-menu.is-opened > .el-sub-menu__title) {
  background-color: var(--el-fill-color-light) !important;
}
.side-menu :deep(.el-sub-menu__title:hover) {
  background-color: var(--el-fill-color-light) !important;
}

.collapse-btn {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
  border-top: 1px solid var(--el-border-color-light);
  flex-shrink: 0;
  transition: background 0.2s, color 0.2s;
}
.collapse-btn:hover {
  background: var(--el-fill-color-light);
  color: #3b82f6;
}

/* 顶部导航 */
.top-header {
  height: 56px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 8px;
  transition: background 0.2s;
}
.user-info:hover {
  background: var(--el-fill-color-light);
}

.username {
  font-size: 14px;
  color: var(--el-text-color-primary);
}

/* 主内容区 */
.main-content {
  background: var(--el-fill-color-lighter);
  overflow-y: auto;
  padding: 20px;
}

.ml-1 {
  margin-left: 4px;
}
</style>
