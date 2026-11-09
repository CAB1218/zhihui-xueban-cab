/**
 * AI4Edu 课堂 API Service
 * 封装课堂互动相关的API调用
 */
import api from './api'

// ============ 类型定义 ============

export interface ClassroomInfo {
  id: string
  name: string
  course_id?: number
  teacher_id: number
  teacher_name?: string
  status: 'waiting' | 'active' | 'ended'
  participant_count: number
  max_participants?: number
  created_at: string
  ended_at?: string
}

export interface ClassroomParticipant {
  id: number
  name: string
  avatar_url?: string
  role: 'teacher' | 'student'
  is_online: boolean
  hand_raised: boolean
  joined_at: string
}

export interface PollItem {
  id: string
  classroom_id: string
  question: string
  options: string[]
  is_active: boolean
  created_at: string
  total_votes: number
}

export interface PollVoteParams {
  option_index: number
}

export interface PollResult {
  poll_id: string
  results: { option: string; count: number; percentage: number }[]
  total_votes: number
}

export interface ClassroomMessage {
  id: string
  classroom_id: string
  user_id: number
  user_name: string
  content: string
  type: 'text' | 'system' | 'hand_raise'
  created_at: string
}

export interface CreateClassroomParams {
  /** 课堂主题，对应后端 ClassroomCreate.title */
  title: string
  /** 后端必填：所属课程 ID */
  course_id?: number
  description?: string
  max_participants?: number
}

export interface CreatePollParams {
  question: string
  options: string[]
}

// ============ API 方法 ============

export const classroomApi = {
  /** 创建课堂 */
  async createClassroom(params: CreateClassroomParams): Promise<ClassroomInfo> {
    // 后端注册在 /classrooms（复数）下，POST 路由为 "/"，故带尾斜杠避免 307
    const response = await api.post('/classrooms/', params)
    return response.data as ClassroomInfo
  },

  /** 获取课堂信息 */
  async getClassroom(classroomId: string): Promise<ClassroomInfo> {
    const response = await api.get(`/classrooms/${classroomId}`)
    return response.data as ClassroomInfo
  },

  /** 加入课堂 */
  async joinClassroom(classroomId: string): Promise<ClassroomInfo> {
    const response = await api.post(`/classrooms/${classroomId}/join`)
    return response.data as ClassroomInfo
  },

  /** 离开课堂 */
  async leaveClassroom(classroomId: string): Promise<void> {
    await api.post(`/classrooms/${classroomId}/leave`)
  },

  /** 举手 */
  async raiseHand(classroomId: string): Promise<void> {
    await api.post(`/classrooms/${classroomId}/raise-hand`)
  },

  /** 创建投票 */
  async createPoll(classroomId: string, params: CreatePollParams): Promise<PollItem> {
    const response = await api.post(`/classrooms/${classroomId}/poll`, params)
    return response.data as PollItem
  },

  /** 投票 */
  async votePoll(classroomId: string, pollId: string, params: PollVoteParams): Promise<void> {
    await api.post(`/classrooms/${classroomId}/poll/${pollId}/vote`, params)
  },

  /** 获取投票结果 */
  async getPollResult(classroomId: string, pollId: string): Promise<PollResult> {
    const response = await api.get(`/classrooms/${classroomId}/poll/${pollId}/result`)
    return response.data as PollResult
  },

  /** 结束课堂 */
  async endClassroom(classroomId: string): Promise<void> {
    await api.post(`/classrooms/${classroomId}/end`)
  },

  /** 获取WebSocket连接URL */
  getWebSocketUrl(classroomId: string): string {
    const baseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
    const token = localStorage.getItem('access_token') || ''
    return `${baseUrl}/ws/classroom/${classroomId}?token=${token}`
  },
}
