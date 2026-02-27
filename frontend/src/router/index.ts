import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/income/dashboard',
    children: [
      // ---- 收入管理模块 ----
      {
        path: 'income/dashboard',
        name: 'IncomeDashboard',
        component: () => import('@/views/income/Dashboard.vue'),
        meta: { title: '收入概览', module: 'income' },
      },
      {
        path: 'income/records',
        name: 'IncomeRecords',
        component: () => import('@/views/income/Records.vue'),
        meta: { title: '收入记录', module: 'income' },
      },
      {
        path: 'income/sources',
        name: 'IncomeSources',
        component: () => import('@/views/income/Sources.vue'),
        meta: { title: '来源管理', module: 'income' },
      },
      // ---- 预留：更多模块在此扩展 ----
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局路由守卫
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn()) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'Login' && auth.isLoggedIn()) {
    return { path: '/' }
  }
})

export default router
