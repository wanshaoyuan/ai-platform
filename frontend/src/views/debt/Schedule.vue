<template>
  <div class="schedule-page">
    <div class="page-toolbar">
      <div class="toolbar-left">
        <el-button text @click="$router.push('/debt/list')">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
        <span class="page-title">{{ debtName }} — 还款计划表</span>
      </div>
      <el-select v-model="statusFilter" style="width: 130px" @change="loadSchedule">
        <el-option label="全部" value="" />
        <el-option label="待还" value="pending" />
        <el-option label="已还" value="paid" />
        <el-option label="逾期" value="overdue" />
      </el-select>
    </div>

    <!-- 债务概览信息条 -->
    <el-card v-if="debtInfo" shadow="never" class="debt-info-bar">
      <el-row :gutter="16">
        <el-col :span="5"><div class="info-item"><span class="info-label">贷款本金</span><span class="info-value">¥{{ fmt(debtInfo.principal) }}</span></div></el-col>
        <el-col :span="5"><div class="info-item"><span class="info-label">当前余额</span><span class="info-value danger">¥{{ fmt(debtInfo.current_balance) }}</span></div></el-col>
        <el-col :span="4"><div class="info-item"><span class="info-label">年化利率</span><span class="info-value">{{ debtInfo.annual_rate }}%</span></div></el-col>
        <el-col :span="5"><div class="info-item"><span class="info-label">月供金额</span><span class="info-value warning">¥{{ fmt(debtInfo.monthly_payment) }}</span></div></el-col>
        <el-col :span="5">
          <div class="info-item">
            <span class="info-label">还款进度</span>
            <span class="info-value">{{ debtInfo.paid_periods }} / {{ debtInfo.term_months }} 期</span>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 还款计划表格 -->
    <el-card shadow="never" class="table-card">
      <el-table
        :data="schedules"
        v-loading="loading"
        stripe
        style="width: 100%"
        :row-class-name="rowClass"
      >
        <el-table-column label="期数" prop="period_no" width="70" align="center" />
        <el-table-column label="应还日期" prop="due_date" width="120" align="center" />
        <el-table-column label="月供总额" align="right" width="130">
          <template #default="{ row }">¥{{ fmt(row.payment_amount) }}</template>
        </el-table-column>
        <el-table-column label="还本金" align="right" width="130">
          <template #default="{ row }">
            <span class="text-blue">¥{{ fmt(row.principal_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="还利息" align="right" width="130">
          <template #default="{ row }">
            <span class="text-orange">¥{{ fmt(row.interest_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="剩余本金" align="right" width="140">
          <template #default="{ row }">¥{{ fmt(row.remaining_balance) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="自动扣减时间" min-width="160">
          <template #default="{ row }">
            <span class="text-gray">{{ row.paid_at ? row.paid_at.replace('T', ' ').slice(0, 19) : '—' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { debtApi, type RepaymentScheduleItem, type DebtItem } from '@/api/debt'

const route = useRoute()
const debtId = Number(route.params.id)

const loading = ref(false)
const schedules = ref<RepaymentScheduleItem[]>([])
const debtInfo = ref<DebtItem | null>(null)
const debtName = ref('')
const statusFilter = ref('')

function fmt(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function statusLabel(s: string) {
  return { pending: '待还', paid: '已还', overdue: '逾期' }[s] ?? s
}

function statusTagType(s: string): '' | 'success' | 'danger' | 'warning' | 'info' {
  return ({ pending: 'warning', paid: 'success', overdue: 'danger' } as any)[s] ?? 'info'
}

function rowClass({ row }: { row: RepaymentScheduleItem }) {
  if (row.status === 'paid') return 'row-paid'
  if (row.status === 'overdue') return 'row-overdue'
  return ''
}

async function loadSchedule() {
  loading.value = true
  try {
    const res = await debtApi.getSchedule(debtId, statusFilter.value as any || undefined)
    schedules.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadDebtInfo() {
  const res = await debtApi.getDebt(debtId)
  debtInfo.value = res.data
  debtName.value = res.data.name
}

onMounted(async () => {
  await Promise.all([loadDebtInfo(), loadSchedule()])
})
</script>

<style scoped>
.schedule-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-size: 15px;
  font-weight: 600;
  color: #2d3748;
}

.debt-info-bar { border-radius: 10px; }
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 11px; color: #9aa3b0; }
.info-value { font-size: 15px; font-weight: 600; color: #1e293b; }
.info-value.danger  { color: #ef4444; }
.info-value.warning { color: #f97316; }

.table-card { border-radius: 10px; }

.text-blue   { color: #3b82f6; }
.text-orange { color: #f97316; }
.text-gray   { color: #9aa3b0; font-size: 12px; }
</style>

<style>
/* 全局行样式（scoped 不生效于 el-table 行） */
.el-table .row-paid td { background-color: rgba(34, 197, 94, 0.05) !important; }
.el-table .row-overdue td { background-color: rgba(239, 68, 68, 0.05) !important; }
</style>
