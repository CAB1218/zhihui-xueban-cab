<template>
  <div class="classroom-dashboard">
    <!-- 场景横幅 -->
    <SceneWelcomeBanner :config="sceneConfig" :demo="!importedCourses.length" />

    <!-- 课堂专属统计卡（今日课程/已完成 会跟随导入的课表变化） -->
    <SceneStatCard :stats="stats" />

    <!-- 当前课程高亮卡 -->
    <CurrentCourseCard :course="currentCourse" @action="handleSubAction" />

    <!-- 今日课表 + 课后复习 -->
    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <TodaySchedule :courses="todayCoursesWithStatus" :source="scheduleSource">
          <template #actions>
            <el-button
              size="small"
              :icon="Upload"
              :loading="scheduleLoading"
              @click="importVisible = true"
            >
              导入课表
            </el-button>
          </template>
          <template #empty-action>
            <el-button type="primary" size="small" :icon="Upload" @click="importVisible = true">
              导入我的课表
            </el-button>
          </template>
        </TodaySchedule>
      </el-col>
      <el-col :xs="24" :lg="10">
        <ReviewReminder :reminders="reviewReminders" @action="handleReminderAction" />
      </el-col>
    </el-row>

    <!-- 课堂工具栏 -->
    <QuickActionBar
      :actions="classroomMockData.toolbarActions"
      title="课堂工具"
      @action="handleAction"
    />

    <!-- 课表导入对话框 -->
    <ScheduleImportDialog v-model="importVisible" @imported="handleImported" />
  </div>
</template>

<script setup lang="ts">
/**
 * 课堂模式仪表盘
 * 组合：场景横幅 + 统计卡 + 当前课程卡 + 今日课表 + 课后复习 + 工具栏
 *
 * 今日课表数据来源：优先用用户自己导入的课表（GET /dashboard/schedule/today），
 * 没有导入过时退回内置示例课表，并在标题旁标注「示例课表」，
 * 让用户清楚看到「这是演示数据，可以导入自己的课表」。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { useSceneStore } from '@/stores/scene'
import { SCENE_CONFIG } from '@/utils/constants'
import dayjs from 'dayjs'
import SceneWelcomeBanner from '../components/SceneWelcomeBanner.vue'
import SceneStatCard from '../components/SceneStatCard.vue'
import QuickActionBar from '../components/QuickActionBar.vue'
import CurrentCourseCard from './components/CurrentCourseCard.vue'
import TodaySchedule from './components/TodaySchedule.vue'
import ReviewReminder from './components/ReviewReminder.vue'
import ScheduleImportDialog from './components/ScheduleImportDialog.vue'
import { classroomMockData } from '../mock/scene-mock-data'
import { CourseStatus } from '../types'
import type { CourseScheduleItem, QuickAction, ReviewReminderItem, StatItem } from '../types'
import scheduleApi, { type ScheduleItem } from '@/services/schedule'

const router = useRouter()
const sceneStore = useSceneStore()

/** 场景配置（从 SCENE_CONFIG 获取） */
const sceneConfig = computed(() => SCENE_CONFIG[sceneStore.currentSceneType])

/** 用户导入的今日课表（为空表示还没导入，走示例数据） */
const importedCourses = ref<ScheduleItem[]>([])
const scheduleLoading = ref(false)
const importVisible = ref(false)

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
  if (importedCourses.value.length) {
    return importedCourses.value.map((item) =>
      computeCourseStatus({
        id: `sched-${item.id}`,
        name: item.name,
        startTime: item.start_time,
        endTime: item.end_time,
        location: item.location,
        teacher: item.teacher,
        status: CourseStatus.UPCOMING,
      }),
    )
  }
  return classroomMockData.todayCourses.map(computeCourseStatus)
})

/** 课表数据来源：imported=用户导入 / demo=示例 / empty=确实没课 */
const scheduleSource = computed<'imported' | 'demo' | 'empty'>(() =>
  importedCourses.value.length ? 'imported' : 'demo',
)

/** 统计卡：今日课程与已完成跟随真实课表，其余沿用仪表盘统计 */
const stats = computed<StatItem[]>(() => {
  if (!importedCourses.value.length) return classroomMockData.stats
  const list = [...classroomMockData.stats]
  const ended = todayCoursesWithStatus.value.filter((c) => c.status === CourseStatus.ENDED).length
  list[0] = { ...list[0], value: todayCoursesWithStatus.value.length }
  list[1] = { ...list[1], value: ended }
  return list
})

/** 课后复习提醒：导入过课表就按当天课程生成，否则用示例 */
const reviewReminders = computed<ReviewReminderItem[]>(() => {
  if (!importedCourses.value.length) return classroomMockData.reviewReminders
  return [...todayCoursesWithStatus.value]
    .slice(0, 3)
    .map((c) => ({
      courseId: c.id,
      courseName: c.name,
      description: `回看「${c.name}」的课堂记录与笔记，整理 3 个关键问题`,
      actionLabel: '开始复习',
      actionRoute: 'notes',
    }))
})

/** 当前正在进行的课程 */
const currentCourse = computed<CourseScheduleItem | null>(() => {
  return todayCoursesWithStatus.value.find(c => c.status === CourseStatus.ONGOING) ?? null
})

/** 拉取今日课表 */
async function loadSchedule(): Promise<void> {
  scheduleLoading.value = true
  try {
    const data = await scheduleApi.getToday()
    importedCourses.value = data.items ?? []
  } catch (e) {
    // 未登录 / 后端不可用时保持示例课表，不打断页面
    console.warn('获取今日课表失败，使用示例课表', e)
    importedCourses.value = []
  } finally {
    scheduleLoading.value = false
  }
}

/** 导入完成：刷新今日课表 */
async function handleImported(payload: { imported: number; today_count?: number }): Promise<void> {
  await loadSchedule()
  if (payload.imported > 0 && (payload.today_count ?? 0) === 0) {
    ElMessage.info('课表已保存，但今天没有排课，可在「今日课表」查看本周其它安排')
  }
}

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

onMounted(loadSchedule)
</script>

<style lang="scss" scoped>
.classroom-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 16px);
}
</style>
