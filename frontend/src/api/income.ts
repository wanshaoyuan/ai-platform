import http from './http'

export interface IncomeSource {
  id: number
  name: string
  icon: string | null
  is_active: boolean
  sort_order: number
  created_at: string
}

export interface IncomeRecord {
  id: number
  source_id: number
  source_name: string
  amount: number
  record_date: string
  note: string | null
  created_at: string
}

export interface RecordListResult {
  total: number
  page: number
  page_size: number
  items: IncomeRecord[]
}

export interface YearlyTrendItem {
  month: number
  total: number
}

export interface MonthlyBreakdownItem {
  source_id: number
  source_name: string
  total: number
  percentage: number
}

export const incomeApi = {
  // ---------- 来源 ----------
  getSources(includeInactive = false) {
    return http.get<IncomeSource[]>('/income/sources', {
      params: { include_inactive: includeInactive },
    })
  },
  createSource(data: { name: string; icon?: string; sort_order?: number }) {
    return http.post<IncomeSource>('/income/sources', data)
  },
  updateSource(id: number, data: Partial<{ name: string; icon: string; is_active: boolean; sort_order: number }>) {
    return http.put<IncomeSource>(`/income/sources/${id}`, data)
  },
  deleteSource(id: number) {
    return http.delete(`/income/sources/${id}`)
  },

  // ---------- 记录 ----------
  getRecords(params: { page?: number; page_size?: number; year?: number; month?: number; source_id?: number }) {
    return http.get<RecordListResult>('/income/records', { params })
  },
  createRecord(data: { source_id: number; amount: number; record_date: string; note?: string }) {
    return http.post<IncomeRecord>('/income/records', data)
  },
  updateRecord(id: number, data: Partial<{ source_id: number; amount: number; record_date: string; note: string }>) {
    return http.put<IncomeRecord>(`/income/records/${id}`, data)
  },
  deleteRecord(id: number) {
    return http.delete(`/income/records/${id}`)
  },

  // ---------- 统计 ----------
  getYearlyTrend(year: number) {
    return http.get<YearlyTrendItem[]>('/income/records/stats/yearly-trend', { params: { year } })
  },
  getMonthlyBreakdown(year: number, month: number) {
    return http.get<MonthlyBreakdownItem[]>('/income/records/stats/monthly-breakdown', {
      params: { year, month },
    })
  },
}
