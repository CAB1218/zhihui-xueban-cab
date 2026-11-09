<template>
  <div :class="['dashboard-view', sceneClass]">
    <!-- 场景推荐提示（跨场景共享逻辑） -->
    <el-alert
      v-if="sceneRecommendation && sceneRecommendation.confidence >= 0.7"
      :title="sceneRecommendation.reason"
      type="info"
      show-icon
      closable
      class="dashboard-view__recommendation"
    >
      <template #default>
        <span>当前场景: {{ sceneName }}</span>
        <el-button
          v-if="sceneRecommendation.recommended_scene !== currentSceneType"
          type="primary"
          link
          @click="switchToRecommended"
        >
          切换到{{ getSceneName(sceneRecommendation.recommended_scene) }}
        </el-button>
      </template>
    </el-alert>

    <!-- 场景仪表盘分发器：按 currentSceneType 动态渲染 -->
    <component :is="dashboardComponent" />
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 场景化仪表盘 — 分发器
 * 根据 currentSceneType 分发到独立场景仪表盘组件
 * 统计数据通过 provide 传递给子组件，避免 prop drilling
 */
import { computed, onMounted, provide, ref } from 'vue'
import { useSceneStore } from '@/stores/scene'
import { SceneType } from '@/utils/constants'
import api from '@/services/api'
import ClassroomDashboard from './classroom/ClassroomDashboard.vue'
import SelfStudyDashboard from './self-study/SelfStudyDashboard.vue'
import ExamDashboard from './exam/ExamDashboard.vue'
import DiscussionDashboard from './discussion/DiscussionDashboard.vue'

const sceneStore = useSceneStore()

/** 场景相关计算属性 */
const sceneName = computed(() => sceneStore.sceneName)
const sceneClass = computed(() => sceneStore.sceneClass)
const currentSceneType = computed(() => sceneStore.currentSceneType)
const sceneRecommendation = computed(() => sceneStore.recommendation)

/** 仪表盘统计（从后端 API 获取，通过 provide 传递给子组件） */
const dashboardStats = ref({
  course_count: 0,
  note_count: 0,
  resource_count: 0,
  ai_chat_count: 0,
  study_hours: '0h',
})

// 向子组件提供统计数据（各场景仪表盘可通过 inject 获取）
provide('dashboardStats', dashboardStats)

/** 场景仪表盘组件映射 */
const dashboardComponent = computed(() => {
  const componentMap: Record<SceneType, typeof ClassroomDashboard> = {
    [SceneType.CLASSROOM]: ClassroomDashboard,
    [SceneType.SELF_STUDY]: SelfStudyDashboard,
    [SceneType.EXAM]: ExamDashboard,
    [SceneType.DISCUSSION]: DiscussionDashboard,
  }
  return componentMap[currentSceneType.value] || ClassroomDashboard
})

/** 场景名称映射 */
const SCENE_NAMES: Record<string, string> = {
  classroom: '课堂模式',
  self_study: '自习模式',
  exam: '考前模式',
  discussion: '讨论模式',
}

function getSceneName(sceneType: string): string {
  return SCENE_NAMES[sceneType] || sceneType
}

/** 切换到推荐场景 */
async function switchToRecommended(): Promise<void> {
  if (sceneRecommendation.value) {
    await sceneStore.switchScene(sceneRecommendation.value.recommended_scene as SceneType)
  }
}

onMounted(async () => {
  // 获取场景推荐
  await sceneStore.getRecommendation()
  // 获取仪表盘统计
  try {
    // api 响应拦截器已解包 axios，res = {code, data: stats, message}
    // 注意：axios 实例的 baseURL 已是 /api/v1，此处不能再带前缀，否则会请求 /api/v1/api/v1/...
    const res = await api.get('/dashboard/stats') as any
    if (res.data) {
      dashboardStats.value = res.data
    }
  } catch (e) {
    console.warn('获取仪表盘统计失败', e)
  }
})
</script>

<style lang="scss" scoped>
.dashboard-view {
  &__recommendation {
    margin-bottom: 16px;
  }
}
</style>
