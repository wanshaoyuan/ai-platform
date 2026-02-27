<template>
  <div class="records-page">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="12" align="middle">
        <el-col :span="5">
          <el-select v-model="filter.year" placeholder="年份" clearable @change="fetchRecords(1)">
            <el-option v-for="y in yearOptions" :key="y" :label="y + ' 年'" :value="y" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filter.month" placeholder="月份" clearable @change="fetchRecords(1)">
            <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filter.source_id" placeholder="收入来源" clearable @change="fetchRecords(1)">
            <el-option v-for="s in sources" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button @click="resetFilter">重置</el-button>
        </el-col>
        <el-col :span="4" style="text-align:right">
          <el-button type="primary" icon="Plus" @click="openDialog()">新增记录</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never">
      <el-table :data="records" v-loading="loading" stripe style="width:100%">
        <el-table-column prop="record_date" label="日期" width="120" sortable />
        <el-table-column prop="source_name" label="来源" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.source_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额（元）" width="140" align="right">
          <template #default="{ row }">
            <span class="amount-text">¥{{ fmt(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" show-overflow-tooltip />
        <el-table-column prop="created_at" label="录入时间" width="180">
          <template #default="{ row }">{{ formatDatetime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" icon="Edit" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="fetchRecords()"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑收入记录' : '新增收入记录'" width="480px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="金额" prop="amount">
          <el-input-number
            v-model="form.amount"
            :min="0.01"
            :precision="2"
            :step="100"
            style="width:100%"
            placeholder="请输入收入金额"
          />
        </el-form-item>
        <el-form-item label="收入来源" prop="source_id">
          <el-select v-model="form.source_id" placeholder="请选择来源" style="width:100%">
            <el-option v-for="s in sources" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" prop="record_date">
          <el-date-picker
            v-model="form.record_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.note"
            type="textarea"
            :rows="3"
            placeholder="选填备注信息"
            maxlength="200"
            show-word-limit
          />
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
import { ref, reactive, onMounted } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessageBox, ElMessage } from 'element-plus'
import { incomeApi, type IncomeRecord, type IncomeSource } from '@/api/income'

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i)

// ---- 列表状态 ----
const records = ref<IncomeRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const sources = ref<IncomeSource[]>([])

const filter = reactive<{ year?: number; month?: number; source_id?: number }>({})

function resetFilter() {
  filter.year = undefined
  filter.month = undefined
  filter.source_id = undefined
  fetchRecords(1)
}

async function fetchRecords(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const res = await incomeApi.getRecords({
      page: page.value,
      page_size: pageSize.value,
      ...filter,
    })
    records.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

// ---- 对话框 ----
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  amount: undefined as number | undefined,
  source_id: undefined as number | undefined,
  record_date: '',
  note: '',
})

const rules: FormRules = {
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
  source_id: [{ required: true, message: '请选择来源', trigger: 'change' }],
  record_date: [{ required: true, message: '请选择日期', trigger: 'change' }],
}

function openDialog(row?: IncomeRecord) {
  editingId.value = row?.id ?? null
  form.amount = row?.amount
  form.source_id = row?.source_id
  form.record_date = row?.record_date ?? ''
  form.note = row?.note ?? ''
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      amount: form.amount!,
      source_id: form.source_id!,
      record_date: form.record_date,
      note: form.note || undefined,
    }
    if (editingId.value) {
      await incomeApi.updateRecord(editingId.value, payload)
      ElMessage.success('记录已更新')
    } else {
      await incomeApi.createRecord(payload)
      ElMessage.success('记录已添加')
    }
    dialogVisible.value = false
    fetchRecords()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: IncomeRecord) {
  await ElMessageBox.confirm(`确认删除 ${row.record_date} 的 ¥${row.amount} 记录？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    confirmButtonClass: 'el-button--danger',
  })
  await incomeApi.deleteRecord(row.id)
  ElMessage.success('已删除')
  fetchRecords()
}

// ---- 工具函数 ----
function fmt(n: number) {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatDatetime(s: string) {
  return s ? s.replace('T', ' ').slice(0, 19) : ''
}

onMounted(async () => {
  const res = await incomeApi.getSources()
  sources.value = res.data
  fetchRecords()
})
</script>

<style scoped>
.records-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card {
  border-radius: 10px;
}

.amount-text {
  font-weight: 600;
  color: #22c55e;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
