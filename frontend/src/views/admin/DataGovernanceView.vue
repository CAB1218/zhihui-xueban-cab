<template>
  <div class="data-governance">
    <div class="data-governance__header">
      <h2>数据治理</h2>
      <el-button type="primary" :loading="scanning" @click="runScan">
        <el-icon><Search /></el-icon> 扫描敏感数据
      </el-button>
    </div>

    <!-- 合规状态仪表盘 -->
    <el-row :gutter="16" class="data-governance__dashboard">
      <el-col :xs="12" :sm="6" v-for="stat in complianceStats" :key="stat.label">
        <div class="data-governance__stat-card">
          <div class="data-governance__stat-icon" :style="{ background: stat.bgColor }">
            <el-icon :size="24" :color="stat.color"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="data-governance__stat-info">
            <span class="data-governance__stat-value">{{ stat.value }}</span>
            <span class="data-governance__stat-label">{{ stat.label }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 数据分类列表 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="data-governance__card">
          <template #header>
            <div class="data-governance__card-header">
              <h3>数据分类</h3>
              <el-button size="small" type="primary" link>管理分类</el-button>
            </div>
          </template>
          <el-table :data="dataCategories" stripe style="width: 100%">
            <el-table-column prop="name" label="分类名称" width="140" />
            <el-table-column prop="level" label="敏感等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getLevelType(row.level)" size="small">{{ row.level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="数据条数" width="100" />
            <el-table-column prop="status" label="合规状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'compliant' ? 'success' : 'danger'" size="small" effect="plain">
                  {{ row.status === 'compliant' ? '合规' : '违规' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>

      <!-- 敏感数据扫描结果 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="data-governance__card">
          <template #header>
            <div class="data-governance__card-header">
              <h3>敏感数据扫描结果</h3>
              <span class="data-governance__scan-time">
                <template v-if="lastScanTime">最近扫描：{{ lastScanTime }}</template>
                <template v-if="scanSummary.tables">
                  　{{ scanSummary.tables }} 表 / {{ scanSummary.columns }} 字段 ｜
                  高 {{ scanSummary.high }} · 中 {{ scanSummary.medium }} · 低 {{ scanSummary.low }}
                </template>
              </span>
            </div>
          </template>
          <div class="data-governance__scan-results">
            <div
              v-for="result in scanResults"
              :key="result.id"
              :class="['data-governance__scan-item', `data-governance__scan-item--${result.severity}`]"
            >
              <div class="data-governance__scan-header">
                <el-tag :type="result.severity === 'high' ? 'danger' : result.severity === 'medium' ? 'warning' : 'info'" size="small">
                  {{ result.severity === 'high' ? '高风险' : result.severity === 'medium' ? '中风险' : '低风险' }}
                </el-tag>
                <span class="data-governance__scan-table">{{ result.table_name }}</span>
              </div>
              <p class="data-governance__scan-desc">{{ result.description }}</p>
              <div class="data-governance__scan-meta">
                <span>字段：{{ result.field }}</span>
                <span>记录数：{{ result.affected_rows }}</span>
              </div>
              <el-button size="small" type="primary" link @click="handleResult(result)">处理</el-button>
            </div>
            <el-empty v-if="scanResults.length === 0" description="未发现敏感数据风险" :image-size="60" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 合规状态仪表盘详细 -->
    <el-card shadow="never" class="data-governance__card" style="margin-top: 16px">
      <template #header>
        <h3>合规状态详情</h3>
      </template>
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="6" v-for="item in complianceItems" :key="item.name">
          <div class="data-governance__compliance-item">
            <div class="data-governance__compliance-header">
              <span class="data-governance__compliance-name">{{ item.name }}</span>
              <el-tag :type="item.status === 'pass' ? 'success' : item.status === 'warning' ? 'warning' : 'danger'" size="small">
                {{ item.status === 'pass' ? '通过' : item.status === 'warning' ? '警告' : '未通过' }}
              </el-tag>
            </div>
            <el-progress
              :percentage="item.score"
              :stroke-width="8"
              :color="item.score >= 90 ? '#67c23a' : item.score >= 70 ? '#e6a23c' : '#f56c6c'"
            />
            <p class="data-governance__compliance-desc">{{ item.description }}</p>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 数据治理页
 * 数据分类列表 + 敏感数据扫描结果 + 合规状态仪表盘
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import api from '@/services/api'

// 合规统计概览
const complianceStats = ref([
  { label: '数据分类覆盖率', value: '96%', icon: 'Folder', color: '#1976D2', bgColor: '#e3f2fd' },
  { label: '敏感数据发现', value: 12, icon: 'Warning', color: '#F57C00', bgColor: '#fff3e0' },
  { label: '合规检查通过率', value: '92%', icon: 'CircleCheck', color: '#388E3C', bgColor: '#e8f5e9' },
  { label: '待处理风险', value: 3, icon: 'Bell', color: '#D32F2F', bgColor: '#ffebee' },
])

// 数据分类
const dataCategories = ref([
  { name: '用户身份信息', level: '高敏感', count: 2580, status: 'compliant', description: '姓名、身份证号、手机号等' },
  { name: '学习行为数据', level: '中敏感', count: 15800, status: 'compliant', description: '学习时长、答题记录、浏览历史' },
  { name: '教学资源数据', level: '低敏感', count: 8900, status: 'compliant', description: '教案、课件、题目资源' },
  { name: 'AI交互数据', level: '中敏感', count: 6200, status: 'non_compliant', description: 'AI对话内容、生成记录' },
  { name: '系统日志数据', level: '低敏感', count: 45000, status: 'compliant', description: '操作日志、访问记录' },
  { name: '成绩评估数据', level: '高敏感', count: 3200, status: 'compliant', description: '考试分数、诊断结果' },
])

// 扫描结果
interface ScanResult {
  id: number
  severity: 'high' | 'medium' | 'low'
  table_name: string
  field: string
  description: string
  affected_rows: number
  handled: boolean
  category?: string
  classification?: string
  suggestion?: string
}

const scanResults = ref<ScanResult[]>([])

const scanning = ref(false)

const lastScanTime = ref<string>('')

const scanSummary = ref<{ tables: number; columns: number; high: number; medium: number; low: number }>({
  tables: 0,
  columns: 0,
  high: 0,
  medium: 0,
  low: 0,
})

// 合规详情
const complianceItems = ref([
  { name: '数据加密存储', score: 95, status: 'pass', description: '敏感数据加密存储覆盖率' },
  { name: '访问权限控制', score: 88, status: 'warning', description: '基于角色的访问控制实施率' },
  { name: '数据脱敏处理', score: 72, status: 'warning', description: '测试和展示环境数据脱敏率' },
  { name: '数据保留策略', score: 60, status: 'fail', description: '按策略清理过期数据执行率' },
])

function getLevelType(level: string): string {
  const map: Record<string, string> = {
    '高敏感': 'danger',
    '中敏感': 'warning',
    '低敏感': 'info',
  }
  return map[level] || ''
}

async function runScan(silent = false): Promise<void> {
  scanning.value = true
  if (!silent) ElMessage.info('开始扫描敏感数据...')
  try {
    const res: any = await api.post('/governance/scan')
    const data = res?.data ?? {}
    scanResults.value = (data.findings ?? []) as ScanResult[]
    scanSummary.value = {
      tables: data.scanned_tables ?? 0,
      columns: data.scanned_columns ?? 0,
      high: data.severity_summary?.high ?? 0,
      medium: data.severity_summary?.medium ?? 0,
      low: data.severity_summary?.low ?? 0,
    }
    lastScanTime.value = data.scanned_at ? new Date(data.scanned_at).toLocaleString('zh-CN') : ''
    if (scanResults.value.length) {
      if (!silent) {
        ElMessage.success(
          `扫描完成：${scanSummary.value.tables} 张表 / ${scanSummary.value.columns} 个字段，发现 ${scanResults.value.length} 处敏感字段`,
        )
      }
    } else if (!silent) {
      ElMessage.success(`扫描完成：${scanSummary.value.tables} 张表，未发现敏感字段`)
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '扫描失败，请稍后重试')
  } finally {
    scanning.value = false
  }
}

function handleResult(result: ScanResult): void {
  ElMessage.info(`处理风险项：${result.description}`)
}

onMounted(() => {
  // 进入页面自动做一次只读扫描，避免展示空表
  runScan(true)
})
</script>

<style lang="scss" scoped>
.data-governance {
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

  &__dashboard {
    margin-bottom: 24px;
  }

  &__stat-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    margin-bottom: 12px;
  }

  &__stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  &__stat-info {
    display: flex;
    flex-direction: column;
  }

  &__stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #303133;
    line-height: 1.2;
  }

  &__stat-label {
    font-size: 13px;
    color: #909399;
    margin-top: 2px;
  }

  &__card {
    margin-bottom: 0;

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin: 0;
    }
  }

  &__card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  &__scan-time {
    font-size: 12px;
    color: #909399;
  }

  &__scan-results {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 400px;
    overflow-y: auto;
  }

  &__scan-item {
    padding: 12px;
    border-radius: 8px;
    border-left: 3px solid #e8e8e8;
    background: #fafafa;

    &--high {
      border-left-color: #f56c6c;
      background: #fff5f5;
    }

    &--medium {
      border-left-color: #e6a23c;
      background: #fdf6ec;
    }

    &--low {
      border-left-color: #909399;
      background: #f9f9f9;
    }
  }

  &__scan-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }

  &__scan-table {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }

  &__scan-desc {
    font-size: 13px;
    color: #606266;
    margin: 0 0 6px;
    line-height: 1.5;
  }

  &__scan-meta {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: #909399;
    margin-bottom: 6px;
  }

  &__compliance-item {
    padding: 14px;
    background: #fafafa;
    border-radius: 8px;
    margin-bottom: 12px;
  }

  &__compliance-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  &__compliance-name {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }

  &__compliance-desc {
    font-size: 12px;
    color: #909399;
    margin: 6px 0 0;
  }
}
</style>
