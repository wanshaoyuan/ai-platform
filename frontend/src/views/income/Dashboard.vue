<template>
  <div class="dashboard">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本年总收入</div>
          <div class="stat-value primary">¥{{ fmt(yearTotal) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">本月总收入</div>
          <div class="stat-value success">¥{{ fmt(monthTotal) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">月均收入</div>
          <div class="stat-value warning">¥{{ fmt(avgMonthly) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">收入来源数</div>
          <div class="stat-value info">{{ sourceCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 年度折线图 -->
    <el-card shadow="never" class="chart-card">
      <template #header>
        <div class="chart-header">
          <span class="chart-title">年度收入趋势</span>
          <el-select v-model="selectedYear" style="width: 100px" @change="loadYearlyData">
            <el-option v-for="y in yearOptions" :key="y" :label="y + ' 年'" :value="y" />
          </el-select>
        </div>
      </template>
      <div ref="lineChartEl" class="chart-container" v-loading="loadingLine" />
    </el-card>

    <!-- 月度柱状图 -->
    <el-card shadow="never" class="chart-card">
      <template #header>
        <div class="chart-header">
          <span class="chart-title">月度收入来源占比</span>
          <div class="chart-header-controls">
            <el-select v-model="breakdownYear" style="width: 100px" @change="loadBreakdownData">
              <el-option v-for="y in yearOptions" :key="y" :label="y + ' 年'" :value="y" />
            </el-select>
            <el-select v-model="breakdownMonth" style="width: 100px; margin-left:8px" @change="loadBreakdownData">
              <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m" />
            </el-select>
          </div>
        </div>
      </template>
      <div ref="barChartEl" class="chart-container" v-loading="loadingBar" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { incomeApi, type YearlyTrendItem, type MonthlyBreakdownItem } from '@/api/income'

// ---- 年份选项 ----
const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i)

// ---- 年度趋势 ----
const selectedYear = ref(currentYear)
const lineChartEl = ref<HTMLDivElement>()
let lineChart: echarts.ECharts | null = null
const loadingLine = ref(false)
const trendData = ref<YearlyTrendItem[]>([])

// ---- 月度分解 ----
const breakdownYear = ref(currentYear)
const breakdownMonth = ref(new Date().getMonth() + 1)
const barChartEl = ref<HTMLDivElement>()
let barChart: echarts.ECharts | null = null
const loadingBar = ref(false)
const breakdownData = ref<MonthlyBreakdownItem[]>([])

// ---- 来源数量 ----
const sourceCount = ref(0)

// ---- 统计值 ----
const yearTotal = computed(() => trendData.value.reduce((s, i) => s + i.total, 0))
const monthTotal = computed(() => {
  const item = trendData.value.find((i) => i.month === new Date().getMonth() + 1)
  return item?.total ?? 0
})
const avgMonthly = computed(() => {
  const nonZero = trendData.value.filter((i) => i.total > 0)
  return nonZero.length ? yearTotal.value / nonZero.length : 0
})

function fmt(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ---- 图表渲染 ----
function renderLineChart() {
  if (!lineChart) return
  const months = trendData.value.map((d) => `${d.month} 月`)
  const totals = trendData.value.map((d) => d.total)

  lineChart.setOption({
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => `¥${fmt(v)}` },
    grid: { left: 60, right: 30, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: months, axisLine: { lineStyle: { color: '#e4e7ed' } } },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => `¥${(v / 1000).toFixed(0)}k` },
    },
    series: [
      {
        name: '月收入',
        type: 'line',
        data: totals,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, color: '#409eff' },
        itemStyle: { color: '#409eff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.3)' },
            { offset: 1, color: 'rgba(64,158,255,0.02)' },
          ]),
        },
      },
    ],
  })
}

function renderBarChart() {
  if (!barChart) return
  const names = breakdownData.value.map((d) => d.source_name)
  const totals = breakdownData.value.map((d) => d.total)
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#9b59b6']

  barChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const item = breakdownData.value[params[0].dataIndex]
        return `${item.source_name}<br/>金额：¥${fmt(item.total)}<br/>占比：${item.percentage}%`
      },
    },
    grid: { left: 60, right: 30, top: 30, bottom: 60 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { rotate: names.length > 4 ? 30 : 0 },
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => `¥${(v / 1000).toFixed(0)}k` },
    },
    series: [
      {
        type: 'bar',
        data: totals.map((v, i) => ({ value: v, itemStyle: { color: colors[i % colors.length] } })),
        barMaxWidth: 60,
        label: {
          show: true,
          position: 'top',
          formatter: (p: any) => {
            const item = breakdownData.value[p.dataIndex]
            return `${item.percentage}%`
          },
        },
      },
    ],
  })
}

async function loadYearlyData() {
  loadingLine.value = true
  try {
    const res = await incomeApi.getYearlyTrend(selectedYear.value)
    trendData.value = res.data
    renderLineChart()
  } finally {
    loadingLine.value = false
  }
}

async function loadBreakdownData() {
  loadingBar.value = true
  try {
    const res = await incomeApi.getMonthlyBreakdown(breakdownYear.value, breakdownMonth.value)
    breakdownData.value = res.data
    renderBarChart()
  } finally {
    loadingBar.value = false
  }
}

async function loadSourceCount() {
  const res = await incomeApi.getSources()
  sourceCount.value = res.data.length
}

onMounted(async () => {
  lineChart = echarts.init(lineChartEl.value!)
  barChart = echarts.init(barChartEl.value!)

  window.addEventListener('resize', () => {
    lineChart?.resize()
    barChart?.resize()
  })

  await Promise.all([loadYearlyData(), loadBreakdownData(), loadSourceCount()])
})

onUnmounted(() => {
  lineChart?.dispose()
  barChart?.dispose()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-row {
  margin-bottom: 0;
}

.stat-card {
  border-radius: 8px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
}
.stat-value.primary { color: #409eff; }
.stat-value.success { color: #67c23a; }
.stat-value.warning { color: #e6a23c; }
.stat-value.info    { color: #606266; }

.chart-card {
  border-radius: 8px;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-header-controls {
  display: flex;
  align-items: center;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.chart-container {
  height: 320px;
  width: 100%;
}
</style>
