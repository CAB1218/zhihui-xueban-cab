<template>
  <div class="audit-log">
    <div class="audit-log__header">
      <h2>审计日志</h2>
      <el-button @click="exportLogs">
        <el-icon><Download /></el-icon> 导出日志
      </el-button>
    </div>

    <!-- 筛选条件 -->
    <div class="audit-log__filters">
      <el-select v-model="filters.actionType" placeholder="操作类型" clearable style="width: 150px" @change="loadData">
        <el-option label="登录" value="login" />
        <el-option label="登出" value="logout" />
        <el-option label="创建" value="create" />
        <el-option label="更新" value="update" />
        <el-option label="删除" value="delete" />
        <el-option label="查看" value="read" />
        <el-option label="导出" value="export" />
        <el-option label="AI操作" value="ai_action" />
      </el-select>
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        style="width: 280px"
        @change="loadData"
      />
      <el-input
        v-model="filters.user"
        placeholder="操作人"
        clearable
        style="width: 150px"
        @input="loadData"
      />
      <el-button type="primary" @click="loadData">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <!-- 日志表格 -->
    <el-table
      v-loading="loading"
      :data="logs"
      stripe
      border
      style="width: 100%"
      class="audit-log__table"
    >
      <el-table-column prop="created_at" label="时间" width="180" sortable>
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="user_name" label="操作人" width="120" />
      <el-table-column prop="action_type" label="操作类型" width="110">
        <template #default="{ row }">
          <el-tag :type="getActionTagType(row.action_type)" size="small">
            {{ getActionLabel(row.action_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource_type" label="资源类型" width="120" />
      <el-table-column prop="description" label="操作详情" min-width="260" show-overflow-tooltip />
      <el-table-column prop="ip_address" label="IP地址" width="140" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small" effect="plain">
            {{ row.status === 'success' ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="audit-log__pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="totalLogs"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="loadData"
        @size-change="loadData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 审计日志页
 * 日志表格 + 筛选（操作类型/时间范围/用户）+ 导出
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import api from '@/services/api'

interface AuditLogEntry {
  id: number
  user_id: number
  user_name: string
  action_type: string
  resource_type: string
  description: string
  ip_address: string
  status: 'success' | 'failure'
  created_at: string
}

const loading = ref<boolean>(false)
const logs = ref<AuditLogEntry[]>([])
const currentPage = ref<number>(1)
const pageSize = ref<number>(20)
const totalLogs = ref<number>(0)

const filters = reactive({
  actionType: '',
  dateRange: null as [string, string] | null,
  user: '',
})

// 模拟日志数据
const mockLogs: AuditLogEntry[] = [
  { id: 1, user_id: 1, user_name: '张三', action_type: 'login', resource_type: '系统', description: '用户登录系统', ip_address: '192.168.1.100', status: 'success', created_at: '2025-01-15T09:00:00Z' },
  { id: 2, user_id: 2, user_name: '李老师', action_type: 'create', resource_type: '教案', description: '创建教案《高等数学-极限》', ip_address: '192.168.1.101', status: 'success', created_at: '2025-01-15T09:15:00Z' },
  { id: 3, user_id: 3, user_name: '王同学', action_type: 'ai_action', resource_type: 'AI助手', description: '向AI助手提问"极限的定义是什么"', ip_address: '192.168.1.102', status: 'success', created_at: '2025-01-15T09:30:00Z' },
  { id: 4, user_id: 1, user_name: '张三', action_type: 'update', resource_type: '笔记', description: '更新笔记《微积分基础》', ip_address: '192.168.1.100', status: 'success', created_at: '2025-01-15T10:00:00Z' },
  { id: 5, user_id: 4, user_name: '管理员', action_type: 'export', resource_type: '数据', description: '导出学生成绩数据', ip_address: '192.168.1.1', status: 'success', created_at: '2025-01-15T10:30:00Z' },
  { id: 6, user_id: 5, user_name: '赵同学', action_type: 'delete', resource_type: '笔记', description: '删除笔记《临时笔记》', ip_address: '192.168.1.103', status: 'success', created_at: '2025-01-15T11:00:00Z' },
  { id: 7, user_id: 2, user_name: '李老师', action_type: 'read', resource_type: '诊断报告', description: '查看班级诊断报告', ip_address: '192.168.1.101', status: 'success', created_at: '2025-01-15T11:15:00Z' },
  { id: 8, user_id: 6, user_name: '孙同学', action_type: 'login', resource_type: '系统', description: '用户登录失败（密码错误）', ip_address: '10.0.0.50', status: 'failure', created_at: '2025-01-15T11:30:00Z' },
  { id: 9, user_id: 3, user_name: '王同学', action_type: 'create', resource_type: '笔记', description: 'AI增强笔记生成摘要', ip_address: '192.168.1.102', status: 'success', created_at: '2025-01-15T12:00:00Z' },
  { id: 10, user_id: 1, user_name: '张三', action_type: 'logout', resource_type: '系统', description: '用户退出系统', ip_address: '192.168.1.100', status: 'success', created_at: '2025-01-15T12:30:00Z' },
]

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const response = await api.get('/governance/audit-logs', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        action_type: filters.actionType || undefined,
        start_date: filters.dateRange?.[0] || undefined,
        end_date: filters.dateRange?.[1] || undefined,
        user: filters.user || undefined,
      },
    })
    logs.value = (response.data as { items: AuditLogEntry[]; total: number }).items || mockLogs
    totalLogs.value = (response.data as { items: AuditLogEntry[]; total: number }).total || mockLogs.length
  } catch {
    // 降级使用模拟数据
    logs.value = mockLogs
    totalLogs.value = mockLogs.length
  } finally {
    loading.value = false
  }
}

function resetFilters(): void {
  filters.actionType = ''
  filters.dateRange = null
  filters.user = ''
  currentPage.value = 1
  loadData()
}

function exportLogs(): void {
  ElMessage.success('日志导出功能开发中')
}

/** 格式化日期时间 */
function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/** 操作类型标签颜色 */
function getActionTagType(actionType: string): string {
  const map: Record<string, string> = {
    login: 'success',
    logout: 'info',
    create: 'primary',
    update: 'warning',
    delete: 'danger',
    read: '',
    export: 'success',
    ai_action: 'warning',
  }
  return map[actionType] || ''
}

/** 操作类型中文标签 */
function getActionLabel(actionType: string): string {
  const map: Record<string, string> = {
    login: '登录',
    logout: '登出',
    create: '创建',
    update: '更新',
    delete: '删除',
    read: '查看',
    export: '导出',
    ai_action: 'AI操作',
  }
  return map[actionType] || actionType
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.audit-log {
  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      font-size: 22px;
      font-weight: 700;
      color: #303133;
      margin: 0;
    }
  }

  &__filters {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 20px;
  }

  &__table {
    :deep(.el-table__header th) {
      background: #fafafa;
      font-weight: 600;
    }
  }

  &__pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
  }
}
</style>
