<template>
  <div class="classroom-dashboard">
    <!-- 场景横幅 -->
    <SceneWelcomeBanner :config="sceneConfig" />

    <!-- 课堂专属统计卡 -->
    <SceneStatCard :stats="classroomMockData.stats" />

    <!-- 当前课程高亮卡 -->
    <CurrentCourseCard :course="currentCourse" @action="handleSubAction" />

    <!-- 今日课表 + 课后复习 -->
    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <TodaySchedule :courses="todayCoursesWithStatus" />
      </el-col>
      <el-col :xs="24" :lg="10">
        <ReviewReminder :reminders="classroomMockData.reviewReminders" @action="handleReminderAction" />
      </el-col>
    </el-row>

    <!-- 课堂工具栏 -->
    <QuickActionBar
      :actions="classroomMockData.toolbarActions"
      title="课堂工具"
      @action="handleAction"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 课堂模式仪表盘
 * 组合：场景横幅 + 统计卡 + 当前课程卡 + 今日课表 + 课后复习 + 工具栏
 * 使用 dayjs 判断课程状态（进行中/已结束/未开始）
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSceneStore } from '@/stores/scene'
import { SCENE_CONFIG } from '@/utils/constants'
import dayjs from 'dayjs'
import SceneWelcomeBanner from '../components/SceneWelcomeBanner.vue'
import SceneStatCard from '../components/SceneStatCard.vue'
import QuickActionBar from '../components/QuickActionBar.vue'
import CurrentCourseCard from './components/CurrentCourseCard.vue'
import TodaySchedule from './components/TodaySchedule.vue'
import ReviewReminder from './components/ReviewReminder.vue'
import { classroomMockData } from '../mock/scene-mock-data'
import { CourseStatus } from '../types'
import type { CourseScheduleItem, QuickAction, ReviewReminderItem } from '../types'

const router = useRouter()
const sceneStore = useSceneStore()

/** 场景配置（从 SCENE_CONFIG 获取） */
const sceneConfig = computed(() => SCENE_CONFIG[sceneStore.currentSceneType])

/**
 * 根据当前时间计算课程状态
 * @param course 课程条目
 * @returns 更新状态后的课程条目
 */
function computeCourseStatus(course: CourseScheduleItem): CourseScheduleItem {
  const now = dayjs()
  const start = dayjs(course.startTime, 'HH:mm')
  const end = dayjs(course.endTime, 'HH:mm')
  let status: CourseStatus
  if (now.isBefore(start)) {
    status = CourseStatus.UPCOMING
  } else if (now.isAfter(end)) {
    status = CourseStatus.ENDED
  } else {
    status = CourseStatus.ONGOING
  }
  return { ...course, status }
}

/** 今日课程（运行时根据当前时间重新计算状态） */
const todayCoursesWithStatus = computed<CourseScheduleItem[]>(() => {
  return classroomMockData.todayCourses.map(computeCourseStatus)
})

/** 当前正在进行的课程 */
const currentCourse = computed<CourseScheduleItem | null>(() => {
  return todayCoursesWithStatus.value.find(c => c.status === CourseStatus.ONGOING) ?? null
})

/**
 * 场景内路由跳转（A-7 统一模式）
 * @param subPath 子路径，如 'notes'、'agent'、'diagnosis'
 */
function navigateToSceneRoute(subPath: string): void {
  const sceneType = sceneStore.currentSceneType
  router.push(`/scene/${sceneType}/${subPath}`)
}

/** 处理工具栏快捷操作 */
function handleAction(action: QuickAction): void {
  navigateToSceneRoute(action.route)
}

/** 处理当前课程卡的操作按钮 */
function handleSubAction(route: string): void {
  navigateToSceneRoute(route)
}

/** 处理课后复习提醒的操作按钮 */
function handleReminderAction(item: ReviewReminderItem): void {
  navigateToSceneRoute(item.actionRoute)
}
</script>

<style lang="scss" scoped>
.classroom-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 16px);
}
</style>
