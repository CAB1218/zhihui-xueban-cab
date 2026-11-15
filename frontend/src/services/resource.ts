/**
 * 智慧学伴 资源管理 API
 */
import api from './api'

// ============ 类型定义 ============

export interface ResourceItem {
  id: number
  title: string
  description?: string
  resource_type: string
  file_size?: number
  mime_type?: string
  thumbnail_url?: string
  tags: string[]
  download_count: number
  view_count: number
  is_public: boolean
  created_at?: string
  updated_at?: string
}

export interface ResourceDetail extends ResourceItem {
  file_key?: string
  url?: string
  preview_url?: string
  course_id?: number
  uploader_id?: number
  metadata?: Record<string, unknown>
}

export interface PaginatedResources {
  items: ResourceItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ResourceUploadResult {
  id: number
  title: string
  resource_type: string
  file_size?: number
  file_key?: string
  created_at?: string
}

// ============ API 方法 ============

export const resourceApi = {
  /** 上传资源 */
  async uploadFile(
    file: File,
    options?: {
      title?: string
      description?: string
      resource_type?: string
      course_id?: number
    },
    onProgress?: (percent: number) => void,
  ): Promise<ResourceUploadResult> {
    const formData = new FormData()
    formData.append('file', file)
    if (options?.title) formData.append('title', options.title)
    if (options?.description) formData.append('description', options.description)
    if (options?.resource_type) formData.append('resource_type', options.resource_type)
    if (options?.course_id) formData.append('course_id', String(options.course_id))

    const response = await api.post('/resources/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded * 100) / e.total))
        }
      },
    })
    return response.data
  },

  /** 创建网页链接资源 */
  async createLink(data: { title: string; url: string; description?: string }): Promise<ResourceDetail> {
    const response = await api.post('/resources/link', data)
    return response.data
  },

  /** 获取资源列表 */
  async listResources(params?: {
    page?: number
    page_size?: number
    resource_type?: string
    search?: string
  }): Promise<PaginatedResources> {
    const response = await api.get('/resources/list', { params })
    return response.data
  },

  /** 获取资源详情 */
  async getResourceDetail(resourceId: number): Promise<ResourceDetail> {
    const response = await api.get(`/resources/${resourceId}`)
    return response.data
  },

  /** 更新资源 */
  async updateResource(resourceId: number, data: Record<string, unknown>): Promise<unknown> {
    const response = await api.put(`/resources/${resourceId}`, null, { params: data })
    return response.data
  },

  /** 删除资源 */
  async deleteResource(resourceId: number): Promise<void> {
    await api.delete(`/resources/${resourceId}`)
  },

  /** 关联知识点 */
  async linkToNode(resourceId: number, nodeId: string): Promise<void> {
    await api.post(`/resources/${resourceId}/link-node`, null, {
      params: { node_id: nodeId },
    })
  },

  /** 取消关联知识点 */
  async unlinkFromNode(resourceId: number, nodeId: string): Promise<void> {
    await api.delete(`/resources/${resourceId}/link-node/${nodeId}`)
  },

  /** 获取预览URL */
  async getPreviewUrl(resourceId: number): Promise<string> {
    const response = await api.get(`/resources/${resourceId}/preview`)
    return response.data.preview_url
  },

  /** AI自动标签 */
  async autoTag(resourceId: number): Promise<string[]> {
    const response = await api.post(`/resources/${resourceId}/auto-tag`)
    return response.data.tags
  },

  /** AI生成摘要 */
  async summarize(resourceId: number): Promise<string> {
    const response = await api.post(`/resources/${resourceId}/summarize`)
    return response.data.summary
  },

  /** 收藏/取消收藏 */
  async toggleFavorite(resourceId: number): Promise<boolean> {
    const response = await api.post(`/resources/${resourceId}/favorite`)
    return response.data.is_favorited
  },
}
