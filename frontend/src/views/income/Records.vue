<template>
  <div class="records-page">
    <div class="page-toolbar">
      <span class="page-title">月度余额录入</span>
      <el-button type="primary" @click="openDialog()">+ 录入月份</el-button>
    </div>

    <!-- 月份快照表格 -->
    <el-card shadow="never" class="table-card" v-loading="loading">
      <el-empty v-if="!loading && snapshots.length === 0" description="暂无记录，点击右上角录入" />

      <el-table v-else :data="snapshots" style="width:100%" stripe>
        <el-table-column label="月份" prop="month" width="110" />
        <el-table-column
          v-for="acc in accounts"
          :key="acc.id"
          :label="acc.name"
          align="right"
          min-width="120"
        >
          <template #default="{ row }">
            <span>{{ fmtCell(row, acc.id) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="总资产" align="right" min-width="130">
          <template #default="{ row }">
            <b>¥{{ fmt(row.total) }}</b>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="openDialog(row.month)">编辑</el-button>
            <el-button size="small" text type="danger" @click="handleDelete(row.month)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 录入/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editMonth ? `编辑 ${editMonth} 余额` : '录入月度余额'"
      width="480px"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="月份" prop="month" :rules="[{ required: true }]">
          <el-date-picker
            v-model="form.month"
            type="month"
            value-format="YYYY-MM"
            placeholder="选择月份"
            :disabled="!!editMonth"
            style="width:100%"
          />
        </el-form-item>
        <el-divider content-position="left" style="margin:8px 0 16px">各账户余额（元）</el-divider>
        <el-form-item
          v-for="acc in accounts"
          :key="acc.id"
          :label="acc.name"
        >
          <el-input-number
            v-model="form.balances[acc.id]"
            :min="0"
            :precision="2"
            :step="1000"
            style="width:100%"
            placeholder="0.00"
          />
        </el-form-item>
        <el-divider style="margin:8px 0 12px" />
        <el-form-item label="合计">
          <span class="total-preview">¥{{ fmt(formTotal) }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { incomeApi, type Account, type MonthlySnapshot } from '@/api/income'

const loading = ref(false)
const snapshots = ref<MonthlySnapshot[]>([])
const accounts = ref<Account[]>([])

function fmt(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtCell(row: MonthlySnapshot, accountId: number) {
  const item = row.items.find(i => i.account_id === accountId)
  return item ? `¥${fmt(item.balance)}` : '—'
}

async function loadData() {
  loading.value = true
  try {
    const [accsRes, snapsRes] = await Promise.all([
      incomeApi.getAccounts(),
      incomeApi.listMonths(60),
    ])
    accounts.value = accsRes.data
    snapshots.value = snapsRes.data
  } finally {
    loading.value = false
  }
}

// ── 弹窗 ─────────────────────────────────────────────────────────────────────
const dialogVisible = ref(false)
const saving = ref(false)
const editMonth = ref<string | null>(null)

const form = reactive({
  month: '',
  balances: {} as Record<number, number>,
})

const formTotal = computed(() =>
  Math.round(Object.values(form.balances).reduce((s, v) => s + (v || 0), 0) * 100) / 100
)

function openDialog(month?: string) {
  editMonth.value = month ?? null
  form.month = month ?? ''
  // 初始化所有账户余额为 0
  accounts.value.forEach(a => { form.balances[a.id] = 0 })

  if (month) {
    const snap = snapshots.value.find(s => s.month === month)
    if (snap) {
      snap.items.forEach(i => { form.balances[i.account_id] = i.balance })
    }
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.month) {
    ElMessage.warning('请选择月份')
    return
  }
  saving.value = true
  try {
    await incomeApi.upsertBalances(
      form.month,
      accounts.value.map(a => ({ account_id: a.id, balance: form.balances[a.id] || 0 }))
    )
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(month: string) {
  await ElMessageBox.confirm(`确认删除 ${month} 的全部余额记录？`, '警告', {
    confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning',
  })
  try {
    await incomeApi.deleteMonth(month)
    ElMessage.success('已删除')
    await loadData()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.records-page { display: flex; flex-direction: column; gap: 16px; }
.page-toolbar {
  display: flex; align-items: center; justify-content: space-between;
}
.page-title { font-size: 16px; font-weight: 600; color: #2d3748; }
.table-card { border-radius: 10px; }
.total-preview { font-size: 18px; font-weight: 700; color: #3b82f6; }
</style>
