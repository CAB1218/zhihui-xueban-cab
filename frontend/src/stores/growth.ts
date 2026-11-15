/**
 * 智慧学伴 学生成长档案 Store
 * 管理成长仪表盘、时间线、教师评价等状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { growthApi } from '@/services/growth'
import type {
  GrowthDashboardData,
  TimelineItem,
  EvaluationItem,
  EvaluationCreateParams,
  EvaluationUpdateParams,
} from '@/services/growth'
import { ElMessage } from 'element-plus'

export const useGrowthStore = defineStore('growth', () => {
  // ============ State ============

  /** 仪表盘数据 */
  const dashboard = ref<GrowthDashboardData | null>(null)
  /** 时间线列表 */
  const timeline = ref<TimelineItem[]>([])
  /** 教师评价列表 */
  const evaluations = ref<EvaluationItem[]>([])
  /** 全局加载状态 */
  const isLoading = ref<boolean>(false)
  /** 时间线是否还有更多 */
  const timelineHasMore = ref<boolean>(false)
  /** 时间线当前页码 */
  const timelinePage = ref<number>(1)
  /** 时间线总条数 */
  const timelineTotal = ref<number>(0)
  /** 时间线筛选来源 */
  const timelineSource = ref<string>('')

  // ============ Getters ============

  /** 最近评价（取前5条） */
  const recentEvaluations = computed<EvaluationItem[]>(() => {
    if (dashboard.value?.recent_evaluations) {
      return dashboard.value.recent_evaluations
    }
    return evaluations.value.slice(0, 5)
  })

  // ============ Actions ============

  /**
   * 获取仪表盘数据
   */
  async function fetchDashboard(studentId?: number): Promise<void> {
    try {
      dashboard.value = await growthApi.getDashboard(studentId)
    } catch (error) {
      console.error('获取成长仪表盘失败:', error)
    }
  }

  /**
   * 获取时间线（重置列表）
   */
  async function fetchTimeline(studentId: number, source?: string): Promise<void> {
    isLoading.value = true
    try {
      timelinePage.value = 1
      timelineSource.value = source || ''
      const res = await growthApi.getTimeline({
        student_id: studentId,
        source: source || undefined,
        page: 1,
      })
      timeline.value = res.items
      timelineTotal.value = res.total
      timelineHasMore.value = res.page < res.total_pages
    } catch (error) {
      console.error('获取成长时间线失败:', error)
      timeline.value = []
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 加载更多时间线
   */
  async function loadMoreTimeline(studentId: number): Promise<void> {
    if (!timelineHasMore.value || isLoading.value) return
    isLoading.value = true
    try {
      const nextPage = timelinePage.value + 1
      const res = await growthApi.getTimeline({
        student_id: studentId,
        source: timelineSource.value || undefined,
        page: nextPage,
      })
      timeline.value.push(...res.items)
      timelinePage.value = nextPage
      timelineHasMore.value = res.page < res.total_pages
    } catch (error) {
      console.error('加载更多时间线失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 获取教师评价列表
   */
  async function fetchEvaluations(studentId: number, page = 1, pageSize = 20): Promise<void> {
    try {
      const res = await growthApi.getEvaluations(studentId, page, pageSize)
      if (page === 1) {
        evaluations.value = res.items
      } else {
        evaluations.value.push(...res.items)
      }
    } catch (error) {
      console.error('获取教师评价失败:', error)
    }
  }

  /**
   * 创建教师评价
   */
  async function createEvaluation(params: EvaluationCreateParams): Promise<EvaluationItem | null> {
    try {
      const evaluation = await growthApi.createEvaluation(params)
      evaluations.value.unshift(evaluation)
      ElMessage.success('评价创建成功')
      return evaluation
    } catch (error) {
      console.error('创建评价失败:', error)
      return null
    }
  }

  /**
   * 更新教师评价
   */
  async function updateEvaluation(evaluationId: number, params: EvaluationUpdateParams): Promise<EvaluationItem | null> {
    try {
      const evaluation = await growthApi.updateEvaluation(evaluationId, params)
      const index = evaluations.value.findIndex((e) => e.id === evaluationId)
      if (index !== -1) {
        evaluations.value[index] = evaluation
      }
      ElMessage.success('评价更新成功')
      return evaluation
    } catch (error) {
      console.error('更新评价失败:', error)
      return null
    }
  }

  /**
   * 删除教师评价
   */
  async function deleteEvaluation(evaluationId: number): Promise<boolean> {
    try {
      await growthApi.deleteEvaluation(evaluationId)
      evaluations.value = evaluations.value.filter((e) => e.id !== evaluationId)
      ElMessage.success('评价已删除')
      return true
    } catch (error) {
      console.error('删除评价失败:', error)
      return false
    }
  }

  return {
    // State
    dashboard,
    timeline,
    evaluations,
    isLoading,
    timelineHasMore,
    timelinePage,
    timelineTotal,
    timelineSource,
    // Getters
    recentEvaluations,
    // Actions
    fetchDashboard,
    fetchTimeline,
    loadMoreTimeline,
    fetchEvaluations,
    createEvaluation,
    updateEvaluation,
    deleteEvaluation,
  }
})
