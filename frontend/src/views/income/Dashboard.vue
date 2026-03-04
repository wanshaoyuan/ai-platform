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

    <!-- 余额趋势折线图（按月/按年切换） -->
    <el-card shadow="never" class="chart-card" v-loading="loadingTrend">
      <template #header>
        <div class="chart-header">
          <span class="chart-title">余额趋势</span>
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
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
            <!-- 按月/按年 切换 -->
            <el-radio-group v-model="viewMode" size="small" @change="onViewModeChange">
              <el-radio-button value="month">按月</el-radio-button>
              <el-radio-button value="year">按年</el-radio-button>
            </el-radio-group>
            <!-- 时间范围 -->
            <el-select
              v-if="viewMode === 'month'"
              v-model="trendMonths"
              style="width:100px"
              @change="loadTrend"
            >
              <el-option label="近 6 月" :value="6" />
              <el-option label="近 12 月" :value="12" />
              <el-option label="近 24 月" :value="24" />
            </el-select>
            <el-select
              v-else
              v-model="trendYears"
              style="width:100px"
              @change="loadTrend"
            >
              <el-option label="近 3 年" :value="3" />
              <el-option label="近 5 年" :value="5" />
              <el-option label="近 10 年" :value="10" />
            </el-select>
          </div>
        </div>
      </template>
      <div ref="lineChartEl" class="chart-container" />
    </el-card>

    <!-- 最新月份各来源余额折线图 -->
    <el-card shadow="never" class="chart-card" v-loading="loadingTrend">
      <template #header>
        <span class="chart-title">{{ snapshots[0]?.month ?? '' }} 各来源余额</span>
      </template>
      <div ref="latestChartEl" class="chart-container" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { incomeApi, type AccountTrend, type MonthlySnapshot } from '@/api/income'

// ── 颜色板 ───────────────────────────────────────────────────────────────────
const PALETTE = [
  '#3b82f6', '#22c55e', '#f59e0b', '#06b6d4',
  '#8b5cf6', '#f87171', '#ec4899', '#14b8a6',
  '#f97316', '#a78bfa',
]
const TOTAL_COLOR = '#1e293b'

const colorMap = new Map<number, string>([[0, TOTAL_COLOR]])
function accountColor(id: number): string {
  if (!colorMap.has(id)) {
    const idx = (colorMap.size - 1) % PALETTE.length
    colorMap.set(id, PALETTE[idx] ?? TOTAL_COLOR)
  }
  return colorMap.get(id) ?? TOTAL_COLOR
}

// ── 视图状态 ──────────────────────────────────────────────────────────────────
const viewMode = ref<'month' | 'year'>('month')
const trendMonths = ref(12)
const trendYears = ref(5)
const loadingTrend = ref(false)
const trendData = ref<AccountTrend[]>([])
const snapshots = ref<MonthlySnapshot[]>([])

const allAccounts = computed(() => trendData.value.filter(a => a.account_id !== 0))
const visibleAccounts = ref<number[]>([])

watch(allAccounts, (list) => {
  if (visibleAccounts.value.length === 0 && list.length > 0) {
    visibleAccounts.value = list.map(a => a.account_id)
    list.forEach(a => accountColor(a.account_id))
  }
}, { immediate: true })

// ── 统计卡片 ──────────────────────────────────────────────────────────────────
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

// ── ECharts ───────────────────────────────────────────────────────────────────
const lineChartEl = ref<HTMLDivElement>()
const latestChartEl = ref<HTMLDivElement>()
let lineChart: echarts.ECharts | null = null
let latestChart: echarts.ECharts | null = null

// 通用折线图渲染（按月趋势 & 按年趋势复用同一函数）
function renderLineChart() {
  if (!lineChart) return
  const totalLine = trendData.value.find(a => a.account_id === 0)
  const xLabels = totalLine?.data.map(d => d.month) ?? []

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
      bottom: 0,
      type: 'scroll',
    },
    grid: { left: 70, right: 20, top: 20, bottom: 50 },
    xAxis: { type: 'category', data: xLabels, boundaryGap: false },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万` },
    },
    series,
  }, true)
}

// 最新月份各来源余额 —— 折线图（X轴为来源名称，一条线）
function renderLatestChart() {
  if (!latestChart || !snapshots.value.length) return
  const latest = snapshots.value[0]
  if (!latest) return

  // 按当前账户顺序排列（allAccounts 已排好序）
  const orderedItems = allAccounts.value
    .map(acc => latest.items.find(i => i.account_id === acc.account_id))
    .filter((i): i is NonNullable<typeof i> => !!i)

  const names = orderedItems.map(i => i.account_name)
  const values = orderedItems.map(i => i.balance)
  const colors = orderedItems.map(i => accountColor(i.account_id))

  latestChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => `${params[0].name}：¥${fmt(params[0].value as number)}`,
    },
    grid: { left: 70, right: 20, top: 20, bottom: 50 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { interval: 0, rotate: names.length > 6 ? 30 : 0 },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万` },
    },
    series: [{
      type: 'line',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: colors[i] ?? TOTAL_COLOR },
      })),
      smooth: true,
      symbolSize: 8,
      lineStyle: { width: 2, color: '#3b82f6' },
      itemStyle: { color: '#3b82f6' },
      label: {
        show: true,
        position: 'top',
        formatter: (p: any) => (p.value as number) > 0 ? `¥${fmt(p.value as number)}` : '',
        fontSize: 11,
        color: '#5a6478',
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,130,246,0.18)' },
          { offset: 1, color: 'rgba(59,130,246,0.01)' },
        ]),
      },
    }],
  })
}

watch(visibleAccounts, renderLineChart)

function onViewModeChange() {
  loadTrend()
}

async function loadTrend() {
  loadingTrend.value = true
  try {
    const [tRes, sRes] = await Promise.all([
      viewMode.value === 'month'
        ? incomeApi.getTrend(trendMonths.value)
        : incomeApi.getTrendYearly(trendYears.value),
      incomeApi.listMonths(trendMonths.value),
    ])
    trendData.value = tRes.data
    snapshots.value = sRes.data
    renderLineChart()
    renderLatestChart()
  } finally {
    loadingTrend.value = false
  }
}

const resizeHandler = () => {
  lineChart?.resize()
  latestChart?.resize()
}

onMounted(async () => {
  lineChart = echarts.init(lineChartEl.value!)
  latestChart = echarts.init(latestChartEl.value!)
  window.addEventListener('resize', resizeHandler)
  await loadTrend()
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  lineChart?.dispose()
  latestChart?.dispose()
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
