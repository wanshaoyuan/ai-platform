<template>
  <div class="debt-dashboard">
    <!-- 顶部汇总数据卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8">
        <el-card shadow="never" class="stat-card stat-card--red">
          <div class="stat-label">总负债余额</div>
          <div class="stat-value danger">¥{{ fmt(summary.total_balance) }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="stat-card stat-card--orange">
          <div class="stat-label">每月总月供</div>
          <div class="stat-value warning">¥{{ fmt(summary.monthly_total_payment) }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="stat-card stat-card--blue">
          <div class="stat-label">有效债务笔数</div>
          <div class="stat-value primary">{{ summary.active_count }} 笔</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 债务余额柱状图 -->
    <el-card shadow="never" class="chart-card" v-loading="loadingChart">
      <template #header>
        <div class="chart-header">
          <span class="chart-title">各项债务余额对比</span>
          <el-button size="small" type="primary" plain @click="$router.push('/debt/list')">
            管理债务
          </el-button>
        </div>
      </template>
      <div v-if="barData.length === 0 && !loadingChart" class="empty-chart">
        <el-empty description="暂无债务数据，请先添加债务" />
      </div>
      <div v-else ref="barChartEl" class="chart-container" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { debtApi, type DebtSummary, type DebtBarItem } from '@/api/debt'

const loadingChart = ref(false)
const barChartEl = ref<HTMLDivElement>()
let barChart: echarts.ECharts | null = null

const summary = ref<DebtSummary>({ total_balance: 0, monthly_total_payment: 0, active_count: 0 })
const barData = ref<DebtBarItem[]>([])

function fmt(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function renderBarChart() {
  if (!barChart || barData.value.length === 0) return
  const colors = ['#ef4444', '#f97316', '#f59e0b', '#3b82f6', '#8b5cf6', '#06b6d4']
  const names = barData.value.map((d) => d.name)
  const balances = barData.value.map((d) => d.current_balance)
  const payments = barData.value.map((d) => d.monthly_payment)

  barChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const idx = params[0].dataIndex
        const d = barData.value[idx]
        if (!d) return ''
        return `
          <b>${d.name}</b><br/>
          剩余本金：¥${fmt(d.current_balance)}<br/>
          每月月供：¥${fmt(d.monthly_payment)}
        `
      },
    },
    legend: { data: ['剩余本金', '月供'], bottom: 0 },
    grid: { left: 70, right: 30, top: 30, bottom: 50 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { rotate: names.length > 4 ? 20 : 0 },
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万` },
    },
    series: [
      {
        name: '剩余本金',
        type: 'bar',
        data: balances.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i % colors.length] },
        })),
        barMaxWidth: 60,
        label: {
          show: true,
          position: 'top',
          formatter: (p: any) => `¥${(p.value / 10000).toFixed(1)}万`,
          fontSize: 11,
          color: '#5a6478',
        },
      },
      {
        name: '月供',
        type: 'bar',
        data: payments.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i % colors.length], opacity: 0.4 },
        })),
        barMaxWidth: 60,
        label: {
          show: true,
          position: 'top',
          formatter: (p: any) => `¥${fmt(p.value)}`,
          fontSize: 11,
          color: '#5a6478',
        },
      },
    ],
  })
}

async function loadData() {
  loadingChart.value = true
  try {
    const [s, b] = await Promise.all([debtApi.getSummary(), debtApi.getBarChart()])
    summary.value = s.data
    barData.value = b.data
    // DOM 更新后初始化图表
    setTimeout(() => {
      if (barChartEl.value && !barChart) {
        barChart = echarts.init(barChartEl.value)
      }
      renderBarChart()
    }, 50)
  } finally {
    loadingChart.value = false
  }
}

const resizeHandler = () => barChart?.resize()

onMounted(async () => {
  window.addEventListener('resize', resizeHandler)
  await loadData()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  barChart?.dispose()
})
</script>

<style scoped>
.debt-dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-card {
  border-radius: 10px;
  border-left: 4px solid transparent;
}
.stat-card--red    { border-left-color: #ef4444; }
.stat-card--orange { border-left-color: #f97316; }
.stat-card--blue   { border-left-color: #3b82f6; }

.stat-label {
  font-size: 12px;
  color: #9aa3b0;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
}
.stat-value { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.stat-value.danger  { color: #ef4444; }
.stat-value.warning { color: #f97316; }
.stat-value.primary { color: #3b82f6; }

.chart-card { border-radius: 10px; }
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.chart-title { font-size: 14px; font-weight: 600; color: #2d3748; }
.chart-container { height: 360px; width: 100%; }
.empty-chart { padding: 40px 0; }
</style>
