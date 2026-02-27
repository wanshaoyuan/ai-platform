<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
      <!-- Logo 区域 -->
      <div class="logo-area">
        <el-icon v-if="isCollapsed" size="24" color="#3b82f6"><Platform /></el-icon>
        <span v-else class="logo-text">AI 中台</span>
      </div>

      <!-- 导航菜单 -->
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        background-color="#ffffff"
        text-color="#5a6478"
        active-text-color="#3b82f6"
        class="side-menu"
      >
        <!-- 收入管理模块 -->
        <el-sub-menu index="income">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>收入管理</span>
          </template>
          <el-menu-item index="/income/dashboard">
            <el-icon><DataLine /></el-icon>
            <span>收入概览</span>
          </el-menu-item>
          <el-menu-item index="/income/records">
            <el-icon><List /></el-icon>
            <span>收入记录</span>
          </el-menu-item>
          <el-menu-item index="/income/sources">
            <el-icon><Setting /></el-icon>
            <span>来源管理</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- 预留模块占位 -->
        <el-menu-item index="placeholder" disabled>
          <el-icon><Plus /></el-icon>
          <span>更多模块（即将上线）</span>
        </el-menu-item>
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
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人信息
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
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isCollapsed = ref(false)

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title as string | undefined)
const userInitial = computed(() =>
  (authStore.user?.username || 'U').charAt(0).toUpperCase()
)

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
  background: #ffffff;
  display: flex;
  flex-direction: column;
  transition: width 0.25s;
  overflow: hidden;
  border-right: 1px solid #eef0f4;
}

.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #eef0f4;
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

.collapse-btn {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #b0b9c8;
  cursor: pointer;
  border-top: 1px solid #eef0f4;
  flex-shrink: 0;
  transition: background 0.2s, color 0.2s;
}
.collapse-btn:hover {
  background: #f5f8ff;
  color: #3b82f6;
}

/* 顶部导航 */
.top-header {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #eef0f4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
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
  background: #f0f6ff;
}

.username {
  font-size: 14px;
  color: #3c4a5e;
}

/* 主内容区 */
.main-content {
  background: #f7f9fc;
  overflow-y: auto;
  padding: 20px;
}

.ml-1 {
  margin-left: 4px;
}
</style>
