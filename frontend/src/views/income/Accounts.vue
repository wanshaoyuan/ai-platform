<template>
  <div class="accounts-page">
    <div class="page-toolbar">
      <span class="page-title">收入来源管理</span>
      <el-button type="primary" @click="openAddDialog">
        <el-icon><Plus /></el-icon> 添加来源
      </el-button>
    </div>

    <el-card shadow="never" class="table-card" v-loading="loading">
      <el-empty v-if="!loading && accounts.length === 0" description="暂无收入来源" />
      <el-table v-else :data="accounts" style="width:100%" row-key="id">
        <el-table-column label="排序" prop="sort_order" width="80" align="center" />
        <el-table-column label="来源名称" prop="name" min-width="160" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '已停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editAccount ? '编辑来源' : '添加来源'"
      width="380px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="80px">
        <el-form-item label="来源名称" prop="name">
          <el-input v-model="form.name" placeholder="如：招商银行、支付宝" maxlength="32" show-word-limit />
        </el-form-item>
        <el-form-item label="排序值" prop="sort_order">
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
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { incomeApi, type Account } from '@/api/income'

const loading = ref(false)
const accounts = ref<Account[]>([])

async function loadAccounts() {
  loading.value = true
  try {
    const res = await incomeApi.getAccounts()
    accounts.value = res.data
  } finally {
    loading.value = false
  }
}

// ── 弹窗 ─────────────────────────────────────────────────────────────────────
const dialogVisible = ref(false)
const saving = ref(false)
const editAccount = ref<Account | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', sort_order: 0 })
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入来源名称', trigger: 'blur' },
    { max: 32, message: '最多 32 个字符', trigger: 'blur' },
  ],
}

function openAddDialog() {
  editAccount.value = null
  form.name = ''
  form.sort_order = accounts.value.length
  dialogVisible.value = true
}

function openEditDialog(acc: Account) {
  editAccount.value = acc
  form.name = acc.name
  form.sort_order = acc.sort_order
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editAccount.value) {
      await incomeApi.updateAccount(editAccount.value.id, {
        name: form.name,
        sort_order: form.sort_order,
      })
      ElMessage.success('来源已更新')
    } else {
      await incomeApi.createAccount(form.name, form.sort_order)
      ElMessage.success('来源已创建')
    }
    dialogVisible.value = false
    await loadAccounts()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(acc: Account) {
  await ElMessageBox.confirm(
    `确认删除「${acc.name}」？删除后该来源的历史余额数据仍保留，但不会再显示在录入列表中。`,
    '警告',
    { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' },
  )
  try {
    await incomeApi.deleteAccount(acc.id)
    ElMessage.success('来源已删除')
    await loadAccounts()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(loadAccounts)
</script>

<style scoped>
.accounts-page { display: flex; flex-direction: column; gap: 16px; }
.page-toolbar {
  display: flex; align-items: center; justify-content: space-between;
}
.page-title { font-size: 16px; font-weight: 600; color: #2d3748; }
.table-card { border-radius: 10px; }
</style>
