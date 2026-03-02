<template>
  <div class="dashboard">
    <!-- 顶部汇总卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card stat-card--blue">
          <div class="stat-label">总资产</div>
          <div class="stat-value primary">¥{{ fmt(latestTotal) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card stat-card--green">
          <div class="stat-label">较上月</div>
          <div class="stat-value" :class="monthDiff >= 0 ? 'success' : 'danger'">
            {{ monthDiff >= 0 ? '+' : '' }}¥{{ fmt(Math.abs(monthDiff)) }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card stat-card--orange">
          <div class="stat-label">已录入月数</div>
          <div class="stat-value warning">{{ snapshots.length }} 个月</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card stat-card--purple">
          <div class="stat-label">最新月份</div>
          <div class="stat-value info">{{ snapshots[0]?.month ?? '—' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图控制栏 -->
    <el-card shadow="never" class="chart-card" v-loading="loadingTrend">
      <template #header>
        <div class="chart-header">
          <span class="chart-title">余额趋势</span>
          <div style="display:flex;align-items:center;gap:12px">
            <!-- 账户筛选 -->
            <el-checkbox-group v-model="visibleAccounts" size="small">
              <el-checkbox-button
                v-for="acc in allAccounts"
                :key="acc.account_id"
                :value="acc.account_id"
                :style="{ '--el-color-primary': accountColor(acc.account_id) }"
              >
                {{ acc.account_name }}
              </el-checkbox-button>
            </el-checkbox-group>
            <!-- 时间范围 -->
            <el-select v-model="trendMonths" style="width:100px" @change="loadTrend">
              <el-option label="近 6 月" :value="6" />
              <el-option label="近 12 月" :value="12" />
              <el-option label="近 24 月" :value="24" />
            </el-select>
          </div>
        </div>
      </template>
      <div ref="lineChartEl" class="chart-container" />
    </el-card>

    <!-- 最新月份各账户余额柱状图 -->
    <el-card shadow="never" class="chart-card" v-loading="loadingTrend">
      <template #header>
        <span class="chart-title">{{ snapshots[0]?.month ?? '' }} 各账户余额</span>
      </template>
      <div ref="barChartEl" class="chart-container" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { incomeApi, type AccountTrend, type MonthlySnapshot } from '@/api/income'

// ── 颜色板（按索引分配，支持任意数量账户）──────────────────────────────────
const PALETTE = [
  '#3b82f6', '#22c55e', '#f59e0b', '#06b6d4',
  '#8b5cf6', '#f87171', '#ec4899', '#14b8a6',
  '#f97316', '#a78bfa',
]
const TOTAL_COLOR = '#1e293b'

// account_id → color（动态生成，0 = 总资产）
const colorMap = new Map<number, string>([[0, TOTAL_COLOR]])
function accountColor(id: number): string {
  if (!colorMap.has(id)) {
    const idx = (colorMap.size - 1) % PALETTE.length
    colorMap.set(id, PALETTE[idx] ?? TOTAL_COLOR)
  }
  return colorMap.get(id) ?? TOTAL_COLOR
}

const loadingTrend = ref(false)
const trendMonths = ref(12)
const trendData = ref<AccountTrend[]>([])
const snapshots = ref<MonthlySnapshot[]>([])

const allAccounts = computed(() => trendData.value.filter(a => a.account_id !== 0))
const visibleAccounts = ref<number[]>([])

// 初始化时默认显示所有账户
watch(allAccounts, (list) => {
  if (visibleAccounts.value.length === 0 && list.length > 0) {
    visibleAccounts.value = list.map(a => a.account_id)
    // 预分配颜色
    list.forEach(a => accountColor(a.account_id))
  }
}, { immediate: true })

// ── 统计卡片数值 ─────────────────────────────────────────────────────────────
const latestTotal = computed(() => snapshots.value[0]?.total ?? 0)
const monthDiff = computed(() => {
  const s = snapshots.value
  if (s.length < 2) return 0
  return round2((s[0]?.total ?? 0) - (s[1]?.total ?? 0))
})

function round2(n: number) { return Math.round(n * 100) / 100 }
function fmt(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ── ECharts ──────────────────────────────────────────────────────────────────
const lineChartEl = ref<HTMLDivElement>()
const barChartEl = ref<HTMLDivElement>()
let lineChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null

function renderLineChart() {
  if (!lineChart) return
  const totalLine = trendData.value.find(a => a.account_id === 0)
  const months = totalLine?.data.map(d => d.month) ?? []

  const series: echarts.SeriesOption[] = []

  if (totalLine) {
    series.push({
      name: '总资产',
      type: 'line',
      data: totalLine.data.map(d => d.value),
      smooth: true,
      lineStyle: { width: 3, color: TOTAL_COLOR },
      itemStyle: { color: TOTAL_COLOR },
      symbolSize: 6,
      z: 10,
    })
  }

  for (const acc of trendData.value.filter(a => a.account_id !== 0)) {
    if (!visibleAccounts.value.includes(acc.account_id)) continue
    const color = accountColor(acc.account_id)
    series.push({
      name: acc.account_name,
      type: 'line',
      data: acc.data.map(d => d.value),
      smooth: true,
      lineStyle: { width: 1.5, color },
      itemStyle: { color },
      symbolSize: 5,
    })
  }

  lineChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) =>
        params.map((p: any) => `${p.seriesName}：¥${fmt(p.value)}`).join('<br/>'),
    },
    legend: {
      data: ['总资产', ...trendData.value.filter(a => a.account_id !== 0).map(a => a.account_name)],
      bottom: 0, type: 'scroll',
    },
    grid: { left: 70, right: 20, top: 20, bottom: 50 },
    xAxis: { type: 'category', data: months, boundaryGap: false },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万` },
    },
    series,
  }, true)
}

function renderBarChart() {
  if (!barChart || !snapshots.value.length) return
  const latest = snapshots.value[0]
  if (!latest) return
  const names = latest.items.map(i => i.account_name)
  const values = latest.items.map(i => i.balance)

  barChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => `${params[0].name}：¥${fmt(params[0].value)}`,
    },
    grid: { left: 80, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: names },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万` },
    },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: accountColor(latest.items[i]?.account_id ?? 0) },
      })),
      barMaxWidth: 60,
      label: {
        show: true, position: 'top',
        formatter: (p: any) => p.value > 0 ? `¥${fmt(p.value)}` : '',
        fontSize: 11, color: '#5a6478',
      },
    }],
  })
}

watch(visibleAccounts, renderLineChart)

async function loadTrend() {
  loadingTrend.value = true
  try {
    const [t, s] = await Promise.all([
      incomeApi.getTrend(trendMonths.value),
      incomeApi.listMonths(trendMonths.value),
    ])
    trendData.value = t.data
    snapshots.value = s.data
    renderLineChart()
    renderBarChart()
  } finally {
    loadingTrend.value = false
  }
}

const resizeHandler = () => { lineChart?.resize(); barChart?.resize() }

onMounted(async () => {
  lineChart = echarts.init(lineChartEl.value!)
  barChart = echarts.init(barChartEl.value!)
  window.addEventListener('resize', resizeHandler)
  await loadTrend()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  lineChart?.dispose()
  barChart?.dispose()
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }
.stat-row { margin-bottom: 0; }

.stat-card {
  border-radius: 10px;
  border-left: 4px solid transparent;
}
.stat-card--blue   { border-left-color: #3b82f6; }
.stat-card--green  { border-left-color: #22c55e; }
.stat-card--orange { border-left-color: #f59e0b; }
.stat-card--purple { border-left-color: #8b5cf6; }

.stat-label {
  font-size: 12px; color: #9aa3b0; margin-bottom: 10px; letter-spacing: 0.5px;
}
.stat-value { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.stat-value.primary { color: #3b82f6; }
.stat-value.success { color: #22c55e; }
.stat-value.danger  { color: #ef4444; }
.stat-value.warning { color: #f59e0b; }
.stat-value.info    { color: #8b5cf6; }

.chart-card { border-radius: 10px; }
.chart-header {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
}
.chart-title { font-size: 14px; font-weight: 600; color: #2d3748; }
.chart-container { height: 320px; width: 100%; }
</style>
