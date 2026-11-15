/**
 * 智慧学伴 学生成长档案 API
 * 提供教师评价 CRUD、成长时间线、成长仪表盘等接口
 */
import api from './api'

// ==================== 类型定义 ====================

export interface EvaluationItem {
  id: number
  student_id: number
  teacher_id: number
  teacher_name: string
  course_id: number | null
  course_name: string | null
  evaluation_type: 'overall' | 'academic' | 'attitude' | 'improvement'
  rating: number
  content: string
  suggestion: string | null
  is_visible: boolean
  created_at: string
  updated_at: string
}

export interface TimelineItem {
  source: 'evaluation' | 'agent' | 'diagnosis' | 'note' | 'flashcard' | 'course' | 'resource' | 'classroom'
  event_type: string
  title: string
  description: string | null
  timestamp: string
  metadata: Record<string, any> | null
}

export interface DashboardStatCard {
  key: string
  label: string
  value: number
  icon: string | null
}

export interface GrowthDashboardData {
  stat_cards: DashboardStatCard[]
  weekly_activity: Array<{ date: string; count: number }>
  subject_distribution: Array<{ subject: string; count: number }>
  recent_evaluations: EvaluationItem[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ==================== 评价参数 ====================

export interface EvaluationCreateParams {
  student_id: number
  course_id?: number
  evaluation_type: string
  rating: number
  content: string
  suggestion?: string
  is_visible?: boolean
}

export interface EvaluationUpdateParams {
  evaluation_type?: string
  rating?: number
  content?: string
  suggestion?: string
  is_visible?: boolean
}

export interface TimelineParams {
  student_id: number
  source?: string
  page?: number
  page_size?: number
}

// ==================== API ====================

export const growthApi = {
  /**
   * 创建教师评价
   * api 拦截器已将 {code,data,message} 解包，直接返回 data 字段内容
   */
  async createEvaluation(params: EvaluationCreateParams): Promise<EvaluationItem> {
    const res = await api.post('/growth/evaluations', params)
    return (res as any).data ?? res
  },

  /**
   * 获取学生评价列表
   */
  async getEvaluations(studentId: number, page = 1, pageSize = 20): Promise<PaginatedResponse<EvaluationItem>> {
    const res = await api.get('/growth/evaluations', {
      params: { student_id: studentId, page, page_size: pageSize },
    })
    return (res as any).data ?? res
  },

  /**
   * 获取单条评价详情
   */
  async getEvaluation(evaluationId: number): Promise<EvaluationItem> {
    const res = await api.get(`/growth/evaluations/${evaluationId}`)
    return (res as any).data ?? res
  },

  /**
   * 更新评价
   */
  async updateEvaluation(evaluationId: number, params: EvaluationUpdateParams): Promise<EvaluationItem> {
    const res = await api.put(`/growth/evaluations/${evaluationId}`, params)
    return (res as any).data ?? res
  },

  /**
   * 删除评价
   */
  async deleteEvaluation(evaluationId: number): Promise<void> {
    await api.delete(`/growth/evaluations/${evaluationId}`)
  },

  /**
   * 获取成长时间线
   */
  async getTimeline(params: TimelineParams): Promise<PaginatedResponse<TimelineItem>> {
    const res = await api.get('/growth/timeline', { params })
    return (res as any).data ?? res
  },

  /**
   * 获取成长仪表盘数据
   */
  async getDashboard(studentId?: number): Promise<GrowthDashboardData> {
    const res = await api.get('/growth/dashboard', {
      params: studentId ? { student_id: studentId } : {},
    })
    return (res as any).data ?? res
  },
}
