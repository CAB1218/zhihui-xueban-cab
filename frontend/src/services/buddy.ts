/**
 * 智慧学伴 学伴 API
 * 封装 /api/v1/buddies/* 接口调用
 */
import request from './api'

// =========== 类型定义 ==========

/** 学伴配置/信息 */
export interface BuddyProfile {
  id?: number
  tenant_id?: number
  user_id?: number
  name: string
  avatar_url: string | null
  personality: string
  tone: string
  interaction_mode: string
  mood?: string
  mood_score?: number
  experience_points?: number
  level?: number
  custom_prompt?: string | null
  settings?: Record<string, any>
  is_active?: boolean
  created_at?: string
  updated_at?: string
}

/** 学伴对话请求 */
export interface BuddyChatRequest {
  message: string
}

/** 学伴对话返回结果（匹配后端 chat() 返回格式） */
export interface BuddyChatResult {
  content: string
  personality?: string
  buddy_name?: string
  buddy_level?: number
}

/** 每日学习报告（匹配后端 get_daily_report() 返回格式） */
export interface BuddyDailyReport {
  date: string
  buddy_name?: string
  buddy_mood?: string
  summary: string
  learning_stats?: {
    questions_answered: number
    notes_created: number
    study_minutes: number
  }
  encouragent?: string
}

/** 学伴心情（匹配后端 get_mood() 返回格式） */
export interface BuddyMoodResult {
  mood: string
  mood_score: number
  level?: number
  experience_points?: number
}

/** 鼓励互动返回 */
export interface BuddyEncourageResult {
  content: string
  action?: string
  mood?: string
  mood_score?: number
}

// =========== API 封装 ==========

/**
 * 获取学伴配置
 */
export async function getBuddyProfile(): Promise<BuddyProfile> {
  const res = await request.get('/api/v1/buddies/profile')
  return (res as any).data ?? res
}

/**
 * 更新学伴配置
 */
export async function updateBuddyProfile(
  data: Partial<Pick<BuddyProfile, 'name' | 'personality' | 'tone' | 'interaction_mode' | 'avatar_url' | 'custom_prompt'>>
): Promise<BuddyProfile> {
  const res = await request.put('/api/v1/buddies/profile', data)
  return (res as any).data ?? res
}

/**
 * 与学伴对话
 */
export async function chatWithBuddy(message: string): Promise<BuddyChatResult> {
  const res = await request.post('/api/v1/buddies/chat', { message })
  return (res as any).data ?? res
}

/**
 * 获取每日学习报告
 */
export async function getDailyReport(): Promise<BuddyDailyReport> {
  const res = await request.get('/api/v1/buddies/daily-report')
  return (res as any).data ?? res
}

/**
 * 获取学伴心情
 */
export async function getBuddyMood(): Promise<BuddyMoodResult> {
  const res = await request.get('/api/v1/buddies/mood')
  return (res as any).data ?? res
}

/**
 * 鼓励学伴互动
 */
export async function encourageBuddy(action = 'praise'): Promise<BuddyEncourageResult> {
  const res = await request.post('/api/v1/buddies/encourage', { action })
  return (res as any).data ?? res
}
