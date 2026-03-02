import http from './http'

export interface Account {
  id: number
  name: string
  sort_order: number
  is_active: boolean
}

export interface BalanceItem {
  account_id: number
  balance: number
}

export interface MonthlyBalanceRead {
  account_id: number
  account_name: string
  balance: number
  updated_at: string
}

export interface MonthlySnapshot {
  month: string
  total: number
  items: MonthlyBalanceRead[]
}

export interface TrendPoint {
  month: string
  value: number
}

export interface AccountTrend {
  account_id: number
  account_name: string
  data: TrendPoint[]
}

export const incomeApi = {
  // 账户列表（首次调用自动初始化默认账户）
  getAccounts() {
    return http.get<Account[]>('/income/accounts')
  },

  // 创建账户
  createAccount(name: string, sort_order = 0) {
    return http.post<Account>('/income/accounts', { name, sort_order })
  },

  // 更新账户
  updateAccount(id: number, data: { name?: string; sort_order?: number }) {
    return http.put<Account>(`/income/accounts/${id}`, data)
  },

  // 删除账户（软删除）
  deleteAccount(id: number) {
    return http.delete(`/income/accounts/${id}`)
  },

  // 所有月份快照列表（倒序）
  listMonths(limit = 24) {
    return http.get<MonthlySnapshot[]>('/income/balances', { params: { limit } })
  },

  // 单月详情
  getMonth(month: string) {
    return http.get<MonthlySnapshot>(`/income/balances/${month}`)
  },

  // 创建/更新某月余额（upsert）
  upsertBalances(month: string, balances: BalanceItem[]) {
    return http.post<MonthlySnapshot>('/income/balances', { month, balances })
  },

  // 删除某月全部记录
  deleteMonth(month: string) {
    return http.delete(`/income/balances/${month}`)
  },

  // 趋势数据（折线图）
  getTrend(months = 12) {
    return http.get<AccountTrend[]>('/income/stats/trend', { params: { months } })
  },

  // 导出 CSV
  exportCsv() {
    return http.get('/income/export/csv', { responseType: 'blob' })
  },

  // 导入 CSV
  importCsv(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return http.post<{ inserted: number; updated: number; skipped: number }>(
      '/income/import/csv',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },
}
