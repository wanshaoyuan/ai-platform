<template>
  <div class="debt-list-page">
    <!-- 顶部操作栏 -->
    <div class="page-toolbar">
      <span class="page-title">债务列表</span>
      <el-button type="primary" @click="openAddDialog">+ 新增债务</el-button>
    </div>

    <!-- 债务卡片列表 -->
    <div v-loading="loading" class="debt-cards">
      <el-empty v-if="!loading && debts.length === 0" description="暂无债务，点击右上角新增" />

      <el-card
        v-for="debt in debts"
        :key="debt.id"
        shadow="never"
        class="debt-card"
        :class="{ 'debt-card--inactive': !debt.is_active }"
      >
        <div class="debt-card-header">
          <div class="debt-name">
            <el-tag :type="debt.is_active ? 'danger' : 'info'" size="small">
              {{ debt.repay_method === 'equal_installment' ? '等额本息' : '等额本金' }}
            </el-tag>
            <span class="name-text">{{ debt.name }}</span>
            <el-tag v-if="!debt.is_active" type="info" size="small">已结清</el-tag>
          </div>
          <div class="debt-actions">
            <el-button size="small" text @click="viewSchedule(debt.id)">还款计划</el-button>
            <el-button size="small" text type="danger" @click="handleDelete(debt)">删除</el-button>
          </div>
        </div>

        <el-row :gutter="12" class="debt-metrics">
          <el-col :span="6">
            <div class="metric-label">贷款本金</div>
            <div class="metric-value">¥{{ fmt(debt.principal) }}</div>
          </el-col>
          <el-col :span="6">
            <div class="metric-label">当前剩余</div>
            <div class="metric-value danger">¥{{ fmt(debt.current_balance) }}</div>
          </el-col>
          <el-col :span="6">
            <div class="metric-label">每月月供</div>
            <div class="metric-value warning">¥{{ fmt(debt.monthly_payment) }}</div>
          </el-col>
          <el-col :span="6">
            <div class="metric-label">年化利率</div>
            <div class="metric-value">{{ debt.annual_rate }}%</div>
          </el-col>
        </el-row>

        <div class="debt-progress">
          <div class="progress-info">
            <span>还款进度：第 {{ debt.paid_periods }} / {{ debt.term_months }} 期</span>
            <span>每月 {{ debt.monthly_repay_day }} 日自动扣减</span>
          </div>
          <el-progress
            :percentage="Math.round(debt.paid_periods / debt.term_months * 100)"
            :color="progressColor(debt)"
            :stroke-width="6"
          />
        </div>

        <div v-if="debt.note" class="debt-note">备注：{{ debt.note }}</div>
      </el-card>
    </div>

    <!-- 新增债务弹窗 -->
    <el-dialog v-model="dialogVisible" title="新增债务" width="540px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="债务名称" prop="name">
          <el-input v-model="form.name" placeholder="如：商业房贷、车贷" />
        </el-form-item>
        <el-form-item label="贷款总额" prop="principal">
          <el-input-number
            v-model="form.principal"
            :min="1"
            :precision="2"
            style="width: 100%"
            placeholder="本金（元）"
          />
        </el-form-item>
        <el-form-item label="年化利率 (%)" prop="annual_rate">
          <el-input-number
            v-model="form.annual_rate"
            :min="0.01"
            :max="36"
            :precision="4"
            style="width: 100%"
            placeholder="如：3.85"
          />
        </el-form-item>
        <el-form-item label="贷款期限" prop="term_months">
          <el-input-number
            v-model="form.term_months"
            :min="1"
            :max="720"
            style="width: 60%"
            placeholder="期数"
          />
          <el-select v-model="termUnit" style="width: 38%; margin-left: 2%" @change="onTermUnitChange">
            <el-option label="月" value="month" />
            <el-option label="年" value="year" />
          </el-select>
        </el-form-item>
        <el-form-item label="还款方式" prop="repay_method">
          <el-select v-model="form.repay_method" style="width: 100%">
            <el-option label="等额本息（月供固定）" value="equal_installment" />
            <el-option label="等额本金（月供递减）" value="equal_principal" />
          </el-select>
        </el-form-item>
        <el-form-item label="首期还款日" prop="first_repay_date">
          <el-date-picker
            v-model="form.first_repay_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择首期还款日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="每月还款日" prop="monthly_repay_day">
          <el-input-number
            v-model="form.monthly_repay_day"
            :min="1"
            :max="31"
            style="width: 100%"
            placeholder="1-31"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>

        <!-- 月供预览 -->
        <el-form-item v-if="previewPayment > 0" label="月供预览">
          <el-tag type="danger" size="large" style="font-size: 16px; padding: 8px 16px;">
            ¥{{ fmt(previewPayment) }} / 月
          </el-tag>
          <span style="margin-left: 8px; color: #9aa3b0; font-size: 12px;">
            （{{ form.repay_method === 'equal_installment' ? '固定月供' : '首期月供，后续递减' }}）
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="default" @click="calcPreview">计算月供</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确认保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { debtApi, type DebtItem } from '@/api/debt'

const router = useRouter()
const loading = ref(false)
const debts = ref<DebtItem[]>([])

// ── 工具函数 ─────────────────────────────────────────────────────────────────
function fmt(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function progressColor(debt: DebtItem) {
  const pct = debt.paid_periods / debt.term_months
  if (pct < 0.3) return '#ef4444'
  if (pct < 0.7) return '#f97316'
  return '#22c55e'
}

// ── 数据加载 ─────────────────────────────────────────────────────────────────
async function loadDebts() {
  loading.value = true
  try {
    const res = await debtApi.listDebts()
    debts.value = res.data
  } finally {
    loading.value = false
  }
}

// ── 新增弹窗 ─────────────────────────────────────────────────────────────────
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const termUnit = ref<'month' | 'year'>('year')
const termYears = ref(30)
const previewPayment = ref(0)

const form = reactive({
  name: '',
  principal: undefined as number | undefined,
  annual_rate: undefined as number | undefined,
  term_months: 360,
  repay_method: 'equal_installment' as 'equal_installment' | 'equal_principal',
  first_repay_date: '',
  monthly_repay_day: undefined as number | undefined,
  note: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入债务名称', trigger: 'blur' }],
  principal: [{ required: true, message: '请输入贷款总额', trigger: 'blur' }],
  annual_rate: [{ required: true, message: '请输入年化利率', trigger: 'blur' }],
  term_months: [{ required: true, message: '请输入贷款期限', trigger: 'blur' }],
  repay_method: [{ required: true }],
  first_repay_date: [{ required: true, message: '请选择首期还款日期', trigger: 'change' }],
  monthly_repay_day: [{ required: true, message: '请输入每月还款日', trigger: 'blur' }],
}

function onTermUnitChange() {
  if (termUnit.value === 'year') {
    form.term_months = termYears.value * 12
  }
}

// 监听 term_months 变化反推年数（仅 year 模式）
watch(() => form.term_months, (v) => {
  if (termUnit.value === 'year') termYears.value = Math.round(v / 12)
})

function openAddDialog() {
  Object.assign(form, {
    name: '', principal: undefined, annual_rate: undefined,
    term_months: 360, repay_method: 'equal_installment',
    first_repay_date: '', monthly_repay_day: undefined, note: '',
  })
  termUnit.value = 'year'
  termYears.value = 30
  previewPayment.value = 0
  dialogVisible.value = true
}

function calcPreview() {
  if (!form.principal || !form.annual_rate || !form.term_months) {
    ElMessage.warning('请先填写本金、年化利率、期数')
    return
  }
  const r = form.annual_rate / 100 / 12
  const n = form.term_months
  const P = form.principal
  if (r === 0) {
    previewPayment.value = Math.round((P / n) * 100) / 100
    return
  }
  if (form.repay_method === 'equal_installment') {
    const factor = Math.pow(1 + r, n)
    previewPayment.value = Math.round(P * r * factor / (factor - 1) * 100) / 100
  } else {
    previewPayment.value = Math.round((P / n + P * r) * 100) / 100
  }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await debtApi.createDebt({
      name: form.name,
      principal: form.principal!,
      annual_rate: form.annual_rate!,
      term_months: form.term_months,
      repay_method: form.repay_method,
      first_repay_date: form.first_repay_date,
      monthly_repay_day: form.monthly_repay_day!,
      note: form.note || undefined,
    })
    ElMessage.success('债务添加成功，还款计划已自动生成')
    dialogVisible.value = false
    await loadDebts()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

// ── 删除 ──────────────────────────────────────────────────────────────────────
async function handleDelete(debt: DebtItem) {
  await ElMessageBox.confirm(`确认删除「${debt.name}」及其所有还款计划？此操作不可撤销。`, '警告', {
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
  try {
    await debtApi.deleteDebt(debt.id)
    ElMessage.success('已删除')
    await loadDebts()
  } catch {
    ElMessage.error('删除失败')
  }
}

// ── 跳转还款计划 ──────────────────────────────────────────────────────────────
function viewSchedule(id: number) {
  router.push(`/debt/schedule/${id}`)
}

onMounted(loadDebts)
</script>

<style scoped>
.debt-list-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
}

.debt-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.debt-card {
  border-radius: 10px;
  border-left: 4px solid #ef4444;
}
.debt-card--inactive {
  border-left-color: #d1d5db;
  opacity: 0.75;
}

.debt-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.debt-name {
  display: flex;
  align-items: center;
  gap: 8px;
}
.name-text {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
.debt-actions {
  display: flex;
  gap: 4px;
}

.debt-metrics {
  margin-bottom: 14px;
}
.metric-label {
  font-size: 12px;
  color: #9aa3b0;
  margin-bottom: 4px;
}
.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}
.metric-value.danger  { color: #ef4444; }
.metric-value.warning { color: #f97316; }

.debt-progress { margin-bottom: 8px; }
.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #9aa3b0;
  margin-bottom: 6px;
}

.debt-note {
  font-size: 12px;
  color: #9aa3b0;
  margin-top: 4px;
}
</style>
