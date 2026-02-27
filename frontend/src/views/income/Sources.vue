<template>
  <div class="sources-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">收入来源管理</span>
          <el-button type="primary" icon="Plus" @click="openDialog()">新增来源</el-button>
        </div>
      </template>

      <el-table :data="sources" v-loading="loading" stripe style="width:100%">
        <el-table-column prop="sort_order" label="排序" width="80" align="center" />
        <el-table-column label="图标" width="70" align="center">
          <template #default="{ row }">
            <span style="font-size:20px">{{ row.icon || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="来源名称" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDatetime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" icon="Edit" @click="openDialog(row)">编辑</el-button>
            <el-button
              text
              :type="row.is_active ? 'warning' : 'success'"
              @click="toggleActive(row)"
            >
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
            <el-button text type="danger" icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑来源' : '新增来源'"
      width="420px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：工资、奖金" maxlength="20" show-word-limit />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="粘贴一个 Emoji，如 💰" maxlength="4" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="999" style="width:100%" />
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
import { incomeApi, type IncomeSource } from '@/api/income'

const sources = ref<IncomeSource[]>([])
const loading = ref(false)

async function fetchSources() {
  loading.value = true
  try {
    const res = await incomeApi.getSources(true)  // 包含停用的
    sources.value = res.data
  } finally {
    loading.value = false
  }
}

// ---- 对话框 ----
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({ name: '', icon: '', sort_order: 0 })

const rules: FormRules = {
  name: [{ required: true, message: '请输入来源名称', trigger: 'blur' }],
}

function openDialog(row?: IncomeSource) {
  editingId.value = row?.id ?? null
  form.name = row?.name ?? ''
  form.icon = row?.icon ?? ''
  form.sort_order = row?.sort_order ?? 0
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = { name: form.name, icon: form.icon || undefined, sort_order: form.sort_order }
    if (editingId.value) {
      await incomeApi.updateSource(editingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await incomeApi.createSource(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    fetchSources()
  } finally {
    saving.value = false
  }
}

async function toggleActive(row: IncomeSource) {
  await incomeApi.updateSource(row.id, { is_active: !row.is_active })
  ElMessage.success(row.is_active ? '已停用' : '已启用')
  fetchSources()
}

async function handleDelete(row: IncomeSource) {
  await ElMessageBox.confirm(
    `确认删除来源「${row.name}」？若该来源存在收入记录则无法删除。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger' }
  )
  await incomeApi.deleteSource(row.id)
  ElMessage.success('已删除')
  fetchSources()
}

function formatDatetime(s: string) {
  return s ? s.replace('T', ' ').slice(0, 19) : ''
}

onMounted(fetchSources)
</script>

<style scoped>
.sources-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
</style>
