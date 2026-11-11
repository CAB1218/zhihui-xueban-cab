<template>
  <div class="today-schedule card">
    <div class="today-schedule__header">
      <div class="today-schedule__title-group">
        <h3 class="today-schedule__title">今日课表</h3>
        <el-tag v-if="source === 'imported'" size="small" effect="plain" type="success">
          已导入
        </el-tag>
        <el-tag v-else-if="source === 'demo'" size="small" effect="plain" type="info">
          示例课表
        </el-tag>
      </div>
      <div class="today-schedule__actions">
        <slot name="actions" />
      </div>
    </div>
    <div v-if="courses.length === 0" class="today-schedule__empty">
      <el-empty description="今天没有课，或还没有导入课表" :image-size="60">
        <slot name="empty-action" />
      </el-empty>
    </div>
    <div v-else class="today-schedule__timeline classroom-timeline">
      <div
        v-for="course in courses"
        :key="course.id"
        class="today-schedule__item"
        :class="[`today-schedule__item--${course.status}`]"
      >
        <!-- 时间轴左侧 -->
        <div class="today-schedule__time">
          <span class="today-schedule__time-start">{{ course.startTime }}</span>
          <span class="today-schedule__time-end">{{ course.endTime }}</span>
        </div>
        <!-- 状态圆点 + 连线 -->
        <div class="today-schedule__dot-wrapper">
          <span class="today-schedule__dot" :class="[`today-schedule__dot--${course.status}`]" />
        </div>
        <!-- 课程信息 -->
        <div class="today-schedule__info">
          <span class="today-schedule__name">{{ course.name }}</span>
          <span class="today-schedule__location">{{ course.location }}</span>
          <span class="today-schedule__teacher">{{ course.teacher }}</span>
        </div>
        <!-- 状态标签 -->
        <el-tag :type="statusTagType(course.status)" size="small" effect="light">
          {{ statusLabel(course.status) }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 今日课表时间轴
 * 时间轴样式：左侧时间 + 状态圆点 + 课程信息 + 状态标签
 */
import { CourseStatus } from '../../types'
import type { CourseScheduleItem } from '../../types'

interface Props {
  /** 今日课程列表 */
  courses: CourseScheduleItem[]
  /** 数据来源：imported=用户导入；demo=内置示例；empty=无数据 */
  source?: 'imported' | 'demo' | 'empty'
}

withDefaults(defineProps<Props>(), {
  source: 'empty',
})

/** 状态对应标签文字 */
function statusLabel(status: CourseStatus): string {
  const map: Record<CourseStatus, string> = {
    [CourseStatus.ONGOING]: '进行中',
    [CourseStatus.ENDED]: '已结束',
    [CourseStatus.UPCOMING]: '未开始',
  }
  return map[status] || '未知'
}

/** 状态对应 el-tag 类型 */
function statusTagType(status: CourseStatus): 'success' | 'info' | 'warning' {
  const map: Record<CourseStatus, 'success' | 'info' | 'warning'> = {
    [CourseStatus.ONGOING]: 'success',
    [CourseStatus.ENDED]: 'info',
    [CourseStatus.UPCOMING]: 'warning',
  }
  return map[status] || 'info'
}
</script>

<style lang="scss" scoped>
.today-schedule {
  min-height: 280px;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  &__title-group {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  &__actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-primary, #303133);
    margin: 0;
  }

  &__timeline {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  &__item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    position: relative;

    &:not(:last-child)::before {
      content: '';
      position: absolute;
      left: 64px;
      top: 28px;
      bottom: -12px;
      width: 2px;
      background: #e0e0e0;
    }
  }

  &__time {
    display: flex;
    flex-direction: column;
    width: 48px;
    flex-shrink: 0;
    text-align: right;

    &-start {
      font-size: 14px;
      font-weight: 600;
      color: var(--color-text-primary, #303133);
    }

    &-end {
      font-size: 11px;
      color: var(--color-text-secondary, #909399);
    }
  }

  &__dot-wrapper {
    width: 16px;
    display: flex;
    justify-content: center;
    flex-shrink: 0;
    z-index: 1;
  }

  &__dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid #fff;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1);

    &--ongoing {
      background: #67C23A;
      animation: classroom-pulse 2s infinite;
    }
    &--ended {
      background: #c0c4cc;
    }
    &--upcoming {
      background: #E6A23C;
    }
  }

  &__info {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  &__name {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-primary, #303133);
  }

  &__location {
    font-size: 12px;
    color: var(--color-text-secondary, #909399);
  }

  &__teacher {
    font-size: 11px;
    color: var(--color-text-secondary, #909399);
  }

  &__empty {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 200px;
  }
}
</style>
