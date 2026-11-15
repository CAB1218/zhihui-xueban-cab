/**
 * 智慧学伴 笔记 API Service
 * 封装笔记相关的API调用
 */
import api from './api'

// ============ 类型定义 ============

export interface NoteItem {
  id: number
  title: string
  content: string
  summary?: string
  note_type: string
  tags: string[]
  course_id?: number
  is_ai_enhanced: boolean
  is_shared: boolean
  version: number
  created_at: string
  updated_at: string
}

export interface NoteDetail extends NoteItem {
  knowledge_nodes?: string[]
  ai_summary?: string
  metadata?: Record<string, unknown>
}

export interface NoteVersion {
  id: number
  note_id: number
  version: number
  content: string
  created_at: string
  change_summary?: string
}

export interface NoteShareInfo {
  share_id: string
  note_id: number
  share_url: string
  is_public: boolean
  expires_at?: string
  created_at: string
}

export interface CreateNoteParams {
  title: string
  content?: string
  note_type?: string
  tags?: string[]
  course_id?: number
}

export interface UpdateNoteParams {
  title?: string
  content?: string
  tags?: string[]
}

export interface AIEnhanceParams {
  enhance_type: 'summarize' | 'extract_points' | 'expand' | 'correct' | 'translate'
  target_content?: string
}

export interface PaginatedNotes {
  items: NoteItem[]
  total: number
  page: number
  page_size: number
}

// ============ API 方法 ============

export const noteApi = {
  /** 获取笔记列表 */
  async listNotes(params?: {
    page?: number
    page_size?: number
    note_type?: string
    search?: string
    course_id?: number
  }): Promise<PaginatedNotes> {
    const response = await api.get('/notes/', { params })
    return response.data as PaginatedNotes
  },

  /** 创建笔记 */
  async createNote(params: CreateNoteParams): Promise<NoteDetail> {
    const response = await api.post('/notes/', params)
    return response.data as NoteDetail
  },

  /** 获取笔记详情 */
  async getNote(noteId: number): Promise<NoteDetail> {
    const response = await api.get(`/notes/${noteId}`)
    return response.data as NoteDetail
  },

  /** 更新笔记 */
  async updateNote(noteId: number, params: UpdateNoteParams): Promise<NoteDetail> {
    const response = await api.put(`/notes/${noteId}`, params)
    return response.data as NoteDetail
  },

  /** 删除笔记 */
  async deleteNote(noteId: number): Promise<void> {
    await api.delete(`/notes/${noteId}`)
  },

  /** AI增强 */
  async aiEnhance(noteId: number, params: AIEnhanceParams): Promise<Record<string, unknown>> {
    const response = await api.post(`/notes/${noteId}/ai-enhance`, params)
    return response.data as Record<string, unknown>
  },

  /** 获取版本历史 */
  async listVersions(noteId: number): Promise<NoteVersion[]> {
    const response = await api.get(`/notes/${noteId}/versions`)
    return response.data as NoteVersion[]
  },

  /** 分享笔记 */
  async shareNote(noteId: number, params?: { is_public?: boolean; expires_in_days?: number }): Promise<NoteShareInfo> {
    const response = await api.post(`/notes/${noteId}/share`, params)
    return response.data as NoteShareInfo
  },
}
