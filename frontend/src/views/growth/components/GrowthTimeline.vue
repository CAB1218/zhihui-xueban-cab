<template>
  <div class="growth-timeline">
    <!-- 筛选栏 -->
    <div class="growth-timeline__filter">
      <el-select
        v-model="currentSource"
        placeholder="全部来源"
        clearable
        size="default"
        style="width: 160px"
        @change="handleFilter"
      >
        <el-option
          v-for="opt in sourceOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </div>

    <!-- 时间线 -->
    <el-skeleton :loading="loading && items.length === 0" :rows="6" animated>
      <template #default>
        <el-empty v-if="items.length === 0" description="暂无成长记录" />
        <el-timeline v-else class="growth-timeline__list">
          <el-timeline-item
            v-for="(item, index) in items"
            :key="index"
            :timestamp="formatTime(item.timestamp)"
            placement="top"
            :type="getSourceColor(item.source)"
            :hollow="false"
          >
            <template #dot>
              <el-icon :size="16" class="timeline-dot__icon">
                <component :is="getSourceIcon(item.source)" />
              </el-icon>
            </template>
            <el-card shadow="hover" class="timeline-card">
              <div class="timeline-card__header">
                <el-tag :type="getSourceTagType(item.source)" size="small" effect="light">
                  {{ getSourceLabel(item.source) }}
                </el-tag>
                <span class="timeline-card__title">{{ item.title }}</span>
              </div>
              <p v-if="item.description" class="timeline-card__desc">{{ item.description }}</p>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-skeleton>

    <!-- 加载更多 -->
    <div v-if="items.length > 0" class="growth-timeline__footer">
      <el-button
        v-if="hasMore"
        type="primary"
        plain
        :loading="loading"
        @click="$emit('load-more')"
      >
        加载更多
      </el-button>
      <span v-else class="growth-timeline__no-more">没有更多了</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 成长时间线组件
 * 展示学生成长记录，支持按来源筛选和分页加载
 */
import { ref } from 'vue'
import {
  ChatDotRound,
  DataAnalysis,
  EditPen,
  Postcard,
  Reading,
  Folder,
  School,
  TrendCharts,
} from '@element-plus/icons-vue'
import type { TimelineItem } from '@/services/growth'

defineProps<{
  items: TimelineItem[]
  loading: boolean
  hasMore: boolean
}>()

const emit = defineEmits<{
  'load-more': []
  filter: [source: string]
}>()

const currentSource = ref<string>('')

/** 来源筛选选项 */
const sourceOptions = [
  { label: '全部', value: '' },
  { label: 'AI对话', value: 'agent' },
  { label: '诊断', value: 'diagnosis' },
  { label: '笔记', value: 'note' },
  { label: '复习卡片', value: 'flashcard' },
  { label: '教师评价', value: 'evaluation' },
  { label: '课程', value: 'course' },
  { label: '资源', value: 'resource' },
  { label: '课堂', value: 'classroom' },
]

/** 来源 → 图标组件映射 */
function getSourceIcon(source: string): any {
  const map: Record<string, any> = {
    agent: ChatDotRound,
    diagnosis: DataAnalysis,
    note: EditPen,
    flashcard: Postcard,
    evaluation: TrendCharts,
    course: Reading,
    resource: Folder,
    classroom: School,
  }
  return map[source] || TrendCharts
}

/** 来源 → 标签文字 */
function getSourceLabel(source: string): string {
  const opt = sourceOptions.find((o) => o.value === source)
  return opt ? opt.label : source
}

/** 来源 → timeline 颜色类型 */
function getSourceColor(source: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
    agent: 'primary',
    diagnosis: 'danger',
    note: 'warning',
    flashcard: 'success',
    evaluation: 'info',
    course: 'primary',
    resource: 'success',
    classroom: 'warning',
  }
  return map[source] || 'info'
}

/** 来源 → tag 类型 */
function getSourceTagType(source: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    agent: '',
    diagnosis: 'danger',
    note: 'warning',
    flashcard: 'success',
    evaluation: 'info',
    course: '',
    resource: 'success',
    classroom: 'warning',
  }
  return map[source] || 'info'
}

/** 格式化时间 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`

  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

function handleFilter(value: string): void {
  emit('filter', value)
}
</script>

<style lang="scss" scoped>
.growth-timeline {
  &__filter {
    margin-bottom: 20px;
  }

  &__list {
    padding-left: 4px;
  }

  &__footer {
    text-align: center;
    padding: 16px 0 8px;
  }

  &__no-more {
    color: #909399;
    font-size: 13px;
  }
}

.timeline-dot__icon {
  color: #fff;
}

.timeline-card {
  :deep(.el-card__body) {
    padding: 12px 16px;
  }

  &__header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__title {
    font-weight: 600;
    font-size: 14px;
    color: #303133;
  }

  &__desc {
    margin: 8px 0 0;
    font-size: 13px;
    color: #606266;
    line-height: 1.6;
  }
}
</style>
