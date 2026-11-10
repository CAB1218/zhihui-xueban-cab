/**
 * AI4Edu 课堂 API Service
 * 封装课堂互动相关的API调用
 */
import api from './api'

// ============ 类型定义 ============

export interface ClassroomInfo {
  id: string | number
  /** 后端字段为 title，name 仅为兼容旧调用 */
  title: string
  name?: string
  access_code?: string
  course_id?: number
  teacher_id: number
  teacher_name?: string
  status: 'scheduled' | 'active' | 'ended'
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

/** 后端 /participants 返回结构 */
export interface ClassroomParticipantInfo {
  user_id: number
  name: string
  avatar_url?: string | null
  role: string
  hand_raised: boolean
  is_online: boolean
  joined_at?: string | null
}

export interface PollItem {
  id: string | number
  classroom_id: string | number
  question: string
  options: string[]
  /** 后端 status 为 active/closed，is_active 由后端同步返回 */
  status?: 'active' | 'closed'
  is_active: boolean
  created_at: string
  total_votes: number
}

export interface PollVoteParams {
  /** 后端字段为 selected_options（索引数组），单选也需传数组 */
  selected_options: number[]
}

export interface PollResult {
  id: string | number
  question: string
  options: string[]
  total_votes: number
  results: { index: number; text: string; count: number; percentage: number }[]
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
  /** 我的课堂列表（教师：我创建的；学生：我加入的） */
  async listClassrooms(): Promise<ClassroomInfo[]> {
    const response = await api.get('/classrooms/')
    return (response.data ?? []) as ClassroomInfo[]
  },

  /** 课堂参与者列表 */
  async getParticipants(classroomId: string | number): Promise<ClassroomParticipantInfo[]> {
    const response = await api.get(`/classrooms/${classroomId}/participants`)
    return (response.data ?? []) as ClassroomParticipantInfo[]
  },

  /** 课堂投票列表 */
  async listPolls(classroomId: string | number): Promise<PollItem[]> {
    const response = await api.get(`/classrooms/${classroomId}/polls`)
    return (response.data ?? []) as PollItem[]
  },

  /** 通过加入码加入课堂 */
  async joinByCode(accessCode: string): Promise<ClassroomInfo> {
    const response = await api.post('/classrooms/join-by-code', { access_code: accessCode })
    return response.data as ClassroomInfo
  },

  /** 创建课堂 */
  async createClassroom(params: CreateClassroomParams): Promise<ClassroomInfo> {
    // 后端注册在 /classrooms（复数）下，POST 路由为 "/"，故带尾斜杠避免 307
    const response = await api.post('/classrooms/', params)
    return response.data as ClassroomInfo
  },

  /** 获取课堂信息 */
  async getClassroom(classroomId: string | number): Promise<ClassroomInfo> {
    const response = await api.get(`/classrooms/${classroomId}`)
    return response.data as ClassroomInfo
  },

  /** 加入课堂 */
  async joinClassroom(classroomId: string | number): Promise<ClassroomInfo> {
    const response = await api.post(`/classrooms/${classroomId}/join`)
    return response.data as ClassroomInfo
  },

  /** 离开课堂 */
  async leaveClassroom(classroomId: string | number): Promise<void> {
    await api.post(`/classrooms/${classroomId}/leave`)
  },

  /** 举手 */
  async raiseHand(classroomId: string | number): Promise<void> {
    await api.post(`/classrooms/${classroomId}/raise-hand`)
  },

  /** 创建投票 */
  async createPoll(classroomId: string | number, params: CreatePollParams): Promise<PollItem> {
    const response = await api.post(`/classrooms/${classroomId}/poll`, params)
    return response.data as PollItem
  },

  /** 投票 */
  async votePoll(classroomId: string | number, pollId: string | number, params: PollVoteParams): Promise<void> {
    await api.post(`/classrooms/${classroomId}/poll/${pollId}/vote`, params)
  },

  /** 获取投票结果 */
  async getPollResult(classroomId: string | number, pollId: string | number): Promise<PollResult> {
    const response = await api.get(`/classrooms/${classroomId}/poll/${pollId}/result`)
    return response.data as PollResult
  },

  /** 结束课堂 */
  async endClassroom(classroomId: string | number): Promise<void> {
    await api.post(`/classrooms/${classroomId}/end`)
  },

  /** 获取WebSocket连接URL */
  getWebSocketUrl(classroomId: string | number): string {
    const baseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
    const token = localStorage.getItem('access_token') || ''
    return `${baseUrl}/ws/classroom/${classroomId}?token=${token}`
  },
}
