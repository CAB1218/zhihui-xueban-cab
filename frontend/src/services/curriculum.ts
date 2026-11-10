/**
 * AI4Edu 课程梳理 API（理解学科-学习内容与要求梳理）
 * 输入课程 → 联网检索+LLM 梳理 → 学习内容与要求清单/必要联系/材料出处
 * 支持 JSON / Markdown / Word 三格式导出
 */
import api from './api'

// ==================== 类型定义 ====================

export interface LearningContent {
  topic: string
  description: string
  requirement: string
  requirement_level: string
  cognitive_level: string
  suggested_hours: number | null
}

export interface OutlineUnit {
  name: string
  description: string
  contents: LearningContent[]
  textbook_ref: string
}

export interface KnowledgeLink {
  from_topic: string
  to_topic: string
  link_type: 'prerequisite' | 'related' | 'cross_subject' | string
  description: string
}

export interface MaterialSource {
  title: string
  url: string
  source_type: 'curriculum_standard' | 'textbook' | 'exam_outline' | 'web' | string
  publisher: string
  usage: string
}

export interface CurriculumOutlineData {
  course: string
  subject: string
  subject_name: string
  grade_level: string
  scope: string
  scope_included?: string[]
  scope_excluded?: string[]
  units: OutlineUnit[]
  connections: KnowledgeLink[]
  sources: MaterialSource[]
  generated_at: string
  model: string
  used_web_search: boolean
  is_sample: boolean
}

export interface CurriculumOutlineRecord {
  id: number
  course_query: string
  subject: string | null
  grade_level: string | null
  scope_hint: string | null
  title: string | null
  outline: CurriculumOutlineData | null
  model_name: string | null
  used_web_search: boolean | null
  status: 'pending' | 'completed' | 'failed' | string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface OutlineGenerateParams {
  course_query: string
  subject?: string
  grade_level?: string
  scope_hint?: string
  use_web_search?: boolean
  fallback_sample?: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ==================== 展示辅助映射 ====================

export const COGNITIVE_LEVEL_MAP: Record<string, string> = {
  remember: '记忆',
  understand: '理解',
  apply: '应用',
  analyze: '分析',
  evaluate: '评价',
  create: '创造',
}

export const LINK_TYPE_MAP: Record<string, { label: string; type: 'primary' | 'success' | 'warning' }> = {
  prerequisite: { label: '前置', type: 'primary' },
  related: { label: '相关', type: 'success' },
  cross_subject: { label: '跨学科', type: 'warning' },
}

export const SOURCE_TYPE_MAP: Record<string, string> = {
  curriculum_standard: '课程标准',
  textbook: '教材',
  exam_outline: '考试大纲',
  web: '网络材料',
}

// ==================== API 调用 ====================

/**
 * 生成课程梳理大纲（联网检索 + LLM，耗时约 30-90 秒）
 */
export async function generateOutline(params: OutlineGenerateParams): Promise<CurriculumOutlineRecord> {
  const res: any = await api.post('/curriculum/outlines', params, { timeout: 180000 })
  // api 拦截器已将 {code,data,message} 返回，取 data 字段内容
  const record: CurriculumOutlineRecord = res?.data ?? res
  return record
}

/**
 * 获取我的课程梳理记录列表
 */
export async function listOutlines(page = 1, pageSize = 20): Promise<PaginatedResponse<CurriculumOutlineRecord>> {
  const res: any = await api.get('/curriculum/outlines', {
    params: { page, page_size: pageSize },
  })
  const payload: PaginatedResponse<CurriculumOutlineRecord> = res?.data ?? res
  return payload
}

/**
 * 获取课程梳理详情
 */
export async function getOutline(id: number): Promise<CurriculumOutlineRecord> {
  const res: any = await api.get(`/curriculum/outlines/${id}`)
  const record: CurriculumOutlineRecord = res?.data ?? res
  return record
}

/**
 * 导出文件下载地址（需带 token，用 downloadExport 下载）
 */
export function exportUrl(id: number, format: 'json' | 'md' | 'docx'): string {
  return `/api/v1/curriculum/outlines/${id}/export?format=${format}`
}

/**
 * 下载导出文件（带鉴权，保存到本地）
 */
export async function downloadExport(id: number, format: 'json' | 'md' | 'docx', filename: string): Promise<void> {
  const res: any = await api.get(`/curriculum/outlines/${id}/export`, {
    params: { format },
    responseType: 'blob',
    timeout: 60000,
  })
  // blob 响应经拦截器后可能直接是 Blob 或包在 data 里
  const raw: BlobPart = res?.data ?? res
  const blob = raw instanceof Blob ? raw : new Blob([raw])
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
