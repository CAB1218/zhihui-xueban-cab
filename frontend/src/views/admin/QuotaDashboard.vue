<template>
  <div class="quota-dashboard">
    <!-- 页头 -->
    <div class="quota-dashboard__header">
      <h2>配额管理看板</h2>
      <el-button type="primary" :icon="Refresh" @click="fetchDashboardData">刷新</el-button>
    </div>

    <!-- 汇总卡片 -->
    <el-row :gutter="16" class="quota-dashboard__summary">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="quota-dashboard__stat-card">
            <div class="quota-dashboard__stat-value">{{ dashboard.total_tenants || 0 }}</div>
            <div class="quota-dashboard__stat-label">租户总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="quota-dashboard__stat-card">
            <div class="quota-dashboard__stat-value">{{ dashboard.active_tenants_today || 0 }}</div>
            <div class="quota-dashboard__stat-label">今日活跃</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="quota-dashboard__stat-card">
            <div class="quota-dashboard__stat-value">{{ formatTokens(dashboard.total_tokens_today) }}</div>
            <div class="quota-dashboard__stat-label">今日总 Token</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="quota-dashboard__stat-card">
            <div
              class="quota-dashboard__stat-value"
              :class="{ 'quota-dashboard__stat-value--warning': exceededCount > 0 }"
            >
              {{ exceededCount }}
            </div>
            <div class="quota-dashboard__stat-label">超限租户</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 模型负载均衡状态 -->
    <el-card shadow="never" class="quota-dashboard__section">
      <template #header>
        <div class="quota-dashboard__section-header">
          <span>模型负载均衡状态</span>
          <el-tag size="small" type="info">{{ balancerStatus.current_strategy || 'latency' }}</el-tag>
        </div>
      </template>
      <el-table :data="balancerStatus.providers || []" stripe>
        <el-table-column prop="provider" label="Provider" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_configured ? 'success' : 'info'" size="small">
              {{ row.provider }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型名称" min-width="150" />
        <el-table-column label="可用状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_available ? 'success' : 'danger'" size="small">
              {{ row.is_available ? '可用' : '不可用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="平均延迟" width="120">
          <template #default="{ row }">
            <span :class="{ 'text-warning': row.avg_latency_ms > 3000 }">
              {{ row.avg_latency_ms > 0 ? `${row.avg_latency_ms.toFixed(0)} ms` : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="成功率" width="100">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.round(row.success_rate * 100)"
              :color="successRateColor(row.success_rate)"
              :stroke-width="14"
              :text-inside="true"
            />
          </template>
        </el-table-column>
        <el-table-column prop="failure_count" label="失败次数" width="100" />
        <el-table-column label="最近检查" width="160">
          <template #default="{ row }">
            {{ row.last_check_time ? formatTimestamp(row.last_check_time) : '未检查' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 租户配额列表 -->
    <el-card shadow="never" class="quota-dashboard__section">
      <template #header>
        <div class="quota-dashboard__section-header">
          <span>租户配额列表</span>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索租户名称"
            :prefix-icon="Search"
            style="width: 240px"
            clearable
            @input="handleSearch"
          />
        </div>
      </template>
      <el-table
        :data="quotaList"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="tenant_id" label="租户 ID" width="80" />
        <el-table-column prop="tenant_name" label="租户名称" min-width="150" />
        <el-table-column label="日额度" width="140">
          <template #default="{ row }">
            <span>{{ formatTokens(row.daily_token_limit) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="月额度" width="140">
          <template #default="{ row }">
            <span>{{ formatTokens(row.monthly_token_limit) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="今日用量" width="180">
          <template #default="{ row }">
            <div class="quota-dashboard__usage-bar">
              <el-progress
                :percentage="calcUsagePercent(row.daily_used_tokens, row.daily_token_limit)"
                :color="usageColor(row.daily_used_tokens, row.daily_token_limit)"
                :stroke-width="12"
                :text-inside="true"
                :format="(_p: number) => `${formatTokens(row.daily_used_tokens)}`"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="本月用量" width="180">
          <template #default="{ row }">
            <div class="quota-dashboard__usage-bar">
              <el-progress
                :percentage="calcUsagePercent(row.monthly_used_tokens, row.monthly_token_limit)"
                :color="usageColor(row.monthly_used_tokens, row.monthly_token_limit)"
                :stroke-width="12"
                :text-inside="true"
                :format="(_p: number) => `${formatTokens(row.monthly_used_tokens)}`"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="balancer_strategy" label="策略" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.balancer_strategy || 'latency' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEditQuota(row)">
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="quota-dashboard__pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchQuotaList"
          @current-change="fetchQuotaList"
        />
      </div>
    </el-card>

    <!-- 编辑配额对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑租户配额" width="480px">
      <el-form :model="editForm" label-width="100px" v-if="editForm">
        <el-form-item label="租户名称">
          <span>{{ editForm.tenant_name }}</span>
        </el-form-item>
        <el-form-item label="日 Token 额度">
          <el-input-number
            v-model="editForm.daily_token_limit"
            :min="10000"
            :max="100000000"
            :step="50000"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="月 Token 额度">
          <el-input-number
            v-model="editForm.monthly_token_limit"
            :min="100000"
            :max="1000000000"
            :step="500000"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="均衡策略">
          <el-select v-model="editForm.balancer_strategy" style="width: 100%">
            <el-option label="延迟优先 (latency)" value="latency" />
            <el-option label="加权随机 (weighted)" value="weighted" />
            <el-option label="粘性绑定 (sticky)" value="sticky" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editForm.balancer_strategy === 'sticky'" label="绑定模型">
          <el-input
            v-model="editForm.sticky_model"
            placeholder="例如: deepseek-chat"
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveQuota">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 配额管理看板
 * 展示租户配额使用情况 + 模型负载均衡状态
 */
import { ref, computed, onMounted } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/services/api'

// ============ State ============

const loading = ref<boolean>(false)
const saving = ref<boolean>(false)
const currentPage = ref<number>(1)
const pageSize = ref<number>(20)
const total = ref<number>(0)
const searchKeyword = ref<string>('')
const searchTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const dashboard = ref<Record<string, any>>({})
const quotaList = ref<Array<Record<string, any>>>([])
const balancerStatus = ref<Record<string, any>>({})
const editDialogVisible = ref<boolean>(false)
const editForm = ref<Record<string, any> | null>(null)

// ============ Computed ============

const exceededCount = computed<number>(() => {
  return quotaList.value.filter(
    (item) => item.daily_token_limit > 0 && item.daily_used_tokens >= item.daily_token_limit
  ).length
})

// ============ Actions ============

/** 获取看板汇总数据 */
async function fetchDashboardData(): Promise<void> {
  loading.value = true
  try {
    const [dashRes, balancerRes] = await Promise.all([
      api.get('/admin/quotas/dashboard'),
      api.get('/agents/models/balancer'),
    ])
    dashboard.value = dashRes.data || {}
    balancerStatus.value = balancerRes.data || {}
  } catch (error) {
    console.error('获取看板数据失败:', error)
    ElMessage.error('获取看板数据失败')
  } finally {
    loading.value = false
  }
}

/** 获取租户配额列表 */
async function fetchQuotaList(): Promise<void> {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    const response = await api.get('/admin/quotas', { params })
    quotaList.value = response.data?.items || []
    total.value = response.data?.total || 0
  } catch (error) {
    console.error('获取配额列表失败:', error)
    ElMessage.error('获取配额列表失败')
  } finally {
    loading.value = false
  }
}

/** 搜索（防抖） */
function handleSearch(): void {
  if (searchTimer.value) clearTimeout(searchTimer.value)
  searchTimer.value = setTimeout(() => {
    currentPage.value = 1
    fetchQuotaList()
  }, 300)
}

/** 打开编辑对话框 */
function handleEditQuota(row: Record<string, any>): void {
  editForm.value = { ...row }
  editDialogVisible.value = true
}

/** 保存配额 */
async function handleSaveQuota(): Promise<void> {
  if (!editForm.value) return
  saving.value = true
  try {
    await api.put(`/admin/quotas/${editForm.value.tenant_id}`, {
      daily_token_limit: editForm.value.daily_token_limit,
      monthly_token_limit: editForm.value.monthly_token_limit,
      balancer_strategy: editForm.value.balancer_strategy,
      sticky_model: editForm.value.sticky_model || null,
    })
    ElMessage.success('配额已更新')
    editDialogVisible.value = false
    await fetchQuotaList()
    await fetchDashboardData()
  } catch (error) {
    console.error('更新配额失败:', error)
    ElMessage.error('更新配额失败')
  } finally {
    saving.value = false
  }
}

// ============ 辅助方法 ============

/** 格式化 Token 数量 */
function formatTokens(tokens: number | undefined): string {
  if (!tokens) return '0'
  if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(0)}K`
  return String(tokens)
}

/** 计算用量百分比 */
function calcUsagePercent(used: number, limit: number): number {
  if (!limit || limit <= 0) return 0
  return Math.min(100, Math.round((used / limit) * 100))
}

/** 用量进度条颜色 */
function usageColor(used: number, limit: number): string {
  const percent = calcUsagePercent(used, limit)
  if (percent >= 90) return '#f44336'
  if (percent >= 70) return '#ff9800'
  return '#4caf50'
}

/** 成功率进度条颜色 */
function successRateColor(rate: number): string {
  if (rate >= 0.95) return '#4caf50'
  if (rate >= 0.8) return '#ff9800'
  return '#f44336'
}

/** 格式化时间戳 */
function formatTimestamp(ts: number): string {
  if (!ts) return '未检查'
  const date = new Date(ts * 1000)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ============ 生命周期 ============

onMounted(async () => {
  await Promise.all([fetchDashboardData(), fetchQuotaList()])
})
</script>

<style lang="scss" scoped>
.quota-dashboard {
  padding: 20px;

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      font-size: 20px;
      font-weight: 600;
      margin: 0;
    }
  }

  &__summary {
    margin-bottom: 20px;
  }

  &__stat-card {
    text-align: center;
    padding: 8px 0;
  }

  &__stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #1976d2;

    &--warning {
      color: #f44336;
    }
  }

  &__stat-label {
    font-size: 13px;
    color: #999;
    margin-top: 4px;
  }

  &__section {
    margin-bottom: 20px;
  }

  &__section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 15px;
    font-weight: 600;
  }

  &__usage-bar {
    min-width: 120px;
  }

  &__pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}

.text-warning {
  color: #ff9800;
  font-weight: 600;
}
</style>
