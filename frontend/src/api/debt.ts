import http from './http'

export type RepayMethod = 'equal_installment' | 'equal_principal'
export type RepayStatus = 'pending' | 'paid' | 'overdue'

export interface DebtItem {
  id: number
  name: string
  principal: number
  annual_rate: number
  term_months: number
  repay_method: RepayMethod
  first_repay_date: string
  monthly_repay_day: number
  monthly_payment: number
  current_balance: number
  paid_periods: number
  is_active: boolean
  note: string | null
  created_at: string
}

export interface DebtItemCreate {
  name: string
  principal: number
  annual_rate: number
  term_months: number
  repay_method?: RepayMethod
  first_repay_date: string
  monthly_repay_day: number
  note?: string
}

export interface RepaymentScheduleItem {
  id: number
  debt_id: number
  period_no: number
  due_date: string
  payment_amount: number
  principal_amount: number
  interest_amount: number
  remaining_balance: number
  status: RepayStatus
  paid_at: string | null
}

export interface DebtSummary {
  total_balance: number
  monthly_total_payment: number
  active_count: number
}

export interface DebtBarItem {
  name: string
  current_balance: number
  monthly_payment: number
}

export const debtApi = {
  // ── 债务 CRUD ──────────────────────────────────────────────────────────────
  listDebts(activeOnly = false) {
    return http.get<DebtItem[]>('/debt', { params: { active_only: activeOnly } })
  },
  createDebt(data: DebtItemCreate) {
    return http.post<DebtItem>('/debt', data)
  },
  getDebt(id: number) {
    return http.get<DebtItem>(`/debt/${id}`)
  },
  updateDebt(id: number, data: Partial<{ name: string; note: string; is_active: boolean }>) {
    return http.put<DebtItem>(`/debt/${id}`, data)
  },
  deleteDebt(id: number) {
    return http.delete(`/debt/${id}`)
  },

  // ── 还款计划表 ─────────────────────────────────────────────────────────────
  getSchedule(debtId: number, statusFilter?: RepayStatus) {
    return http.get<RepaymentScheduleItem[]>(`/debt/${debtId}/schedule`, {
      params: statusFilter ? { status: statusFilter } : {},
    })
  },

  // ── 统计 ───────────────────────────────────────────────────────────────────
  getSummary() {
    return http.get<DebtSummary>('/debt/stats/summary')
  },
  getBarChart() {
    return http.get<DebtBarItem[]>('/debt/stats/bar-chart')
  },
}
