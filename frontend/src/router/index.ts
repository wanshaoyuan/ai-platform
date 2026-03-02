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
      // ---- 余额管理模块 ----
      {
        path: 'income/dashboard',
        name: 'IncomeDashboard',
        component: () => import('@/views/income/Dashboard.vue'),
        meta: { title: '余额概览', module: 'income' },
      },
      {
        path: 'income/records',
        name: 'IncomeRecords',
        component: () => import('@/views/income/Records.vue'),
        meta: { title: '余额录入', module: 'income' },
      },
      {
        path: 'income/accounts',
        name: 'IncomeAccounts',
        component: () => import('@/views/income/Accounts.vue'),
        meta: { title: '账户管理', module: 'income' },
      },
      // ---- 预留：更多模块在此扩展 ----
      // ---- 债务管理模块 ----
      {
        path: 'debt/dashboard',
        name: 'DebtDashboard',
        component: () => import('@/views/debt/Dashboard.vue'),
        meta: { title: '债务概览', module: 'debt' },
      },
      {
        path: 'debt/list',
        name: 'DebtList',
        component: () => import('@/views/debt/Debts.vue'),
        meta: { title: '债务管理', module: 'debt' },
      },
      {
        path: 'debt/schedule/:id',
        name: 'DebtSchedule',
        component: () => import('@/views/debt/Schedule.vue'),
        meta: { title: '还款计划', module: 'debt' },
      },
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
