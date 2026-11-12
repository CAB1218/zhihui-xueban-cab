/**
 * AI4EDU 知识图谱 API
 */
import api from './api'

// ============ 类型定义 ============

export interface SquareStat {
  id: string
  name: string
  icon: string
  color: string
  node_count: number
  completeness: number
  misconception_count: number
}

export interface KnowledgeNode {
  id: string
  name: string
  subject?: string
  subject_id?: string
  node_type?: 'subject' | 'knowledge'
  color?: string
  description?: string
  cognitive_level?: Record<string, number>
  has_misconception?: boolean
  misconceptions?: Misconception[]
  [key: string]: unknown
}

/**
 * 力导图通用节点类型（ForceGraph 组件与各个图谱视图的公共契约）
 * d3 运行时会把 x/y 坐标注入节点对象
 */
export interface GraphNode {
  id: string
  name?: string
  subject?: string
  subject_id?: string
  node_type?: 'subject' | 'knowledge'
  color?: string
  description?: string | null
  has_misconception?: boolean
  x?: number
  y?: number
}

export interface GraphLink {
  /** d3 力导运行后，source/target 会被替换为节点对象，因此是联合类型 */
  source: string | GraphNode
  target: string | GraphNode
  type: string
  label: string
  strength?: number
  strength_label?: '强' | '中' | '弱'
  is_cross?: boolean
}

export interface NeighborData {
  nodes: KnowledgeNode[]
  links: GraphLink[]
}

export interface CognitiveGoal {
  dimensions: string[]
  dimension_keys?: string[]
  values: number[]
  subject_avg?: number[] | null
  node_name: string
}

// ========== Misconception 类型 ==========

export interface Misconception {
  mc_id: string
  misconception: string
  correction: string
  topic: string
  keywords: string[]
  source: 'teacher' | 'ai' | 'system'
  annotated_by: number | null
  annotated_at: string
  confidence: number
}

export interface MisconceptionInput {
  misconception: string
  correction: string
  topic: string
  keywords: string[]
}

export interface MisconceptionSuggestion {
  misconception: string
  correction: string
  topic: string
  keywords: string[]
  subject: string
  confidence: number
}

export interface AutoSuggestResponse {
  suggestions: MisconceptionSuggestion[]
  total: number
}

// ========== 跨学科图谱类型 ==========

export interface CrossSubjectNode {
  id: string
  name: string
  subject: string
  subject_id?: string
  node_type?: 'subject' | 'knowledge'
  color?: string
  description?: string | null
  has_misconception: boolean
  degree: number
}

export interface CrossSubjectLink {
  source: string
  target: string
  type: string
  label: string
  is_cross: boolean
  strength: number
  strength_label: '强' | '中' | '弱'
}

export interface CrossSubjectStats {
  total_nodes: number
  total_links: number
  cross_links: number
  avg_strength: number
  subject_distribution: Record<string, number>
  top_cross_pairs?: Array<{
    source: string
    target: string
    strength: number
    strength_label: '强' | '中' | '弱'
  }>
}

export interface CrossSubjectResponse {
  nodes: CrossSubjectNode[]
  links: CrossSubjectLink[]
  stats: CrossSubjectStats
}

// ========== 任务类型 ==========

export interface NodeTask {
  task_id: string
  name: string
  type: 'learning' | 'review' | 'diagnosis'
  status: 'pending' | 'in_progress' | 'completed'
  due_date: string | null
  source: 'course' | 'diagnosis' | 'teacher'
  description?: string
  assigned_by?: number
}

export type GraphChangeType =
  | 'overview'
  | 'cognitive'
  | 'relationship'
  | 'relationship_delete'
  | 'recommendation'
  | 'recommendation_delete'
  | 'resource_link'
  | 'resource_update'
  | 'resource_unlink'

export interface GraphChangeRequest {
  id: string
  node_id: string
  change_type: GraphChangeType
  payload: Record<string, unknown>
  status: 'pending' | 'approved' | 'rejected'
  submitted_by: number
  reviewer_id?: number
  review_comment?: string
  created_at: string
}

export interface GraphChangeResult {
  status: 'approved' | 'pending'
  applied?: unknown
  id?: string
}

// ============ API 方法 ============

/** 知识点批量导入结果 */
export interface KnowledgeImportResult {
  total: number
  created: number
  skipped: number
  failed: number
  links: number
  created_rows: Array<{ name: string; id?: string }>
  skipped_rows: Array<{ name: string; reason: string }>
  errors: Array<{ row: number; reasons: string[]; raw?: Record<string, unknown> }>
  errors_truncated?: boolean
  node_count: number
}

export const graphApi = {
  /** 获取图谱广场统计 */
  async getSquareStats(): Promise<SquareStat[]> {
    const response = await api.get('/graphs/square')
    return response.data
  },

  /** 获取节点详情 */
  async getNodeDetail(nodeId: string): Promise<KnowledgeNode> {
    const response = await api.get(`/graphs/nodes/${nodeId}`)
    return response.data
  },

  /** 获取邻居节点 */
  async getNeighbors(nodeId: string, depth = 1, limit = 50): Promise<NeighborData> {
    const response = await api.get(`/graphs/nodes/${nodeId}/neighbors`, {
      params: { depth, limit },
    })
    return response.data
  },

  /** 获取节点关联资源 */
  async getNodeResources(nodeId: string): Promise<unknown[]> {
    const response = await api.get(`/graphs/nodes/${nodeId}/resources`)
    return response.data
  },

  /** 获取推荐节点 */
  async getRecommendations(nodeId: string, limit = 10): Promise<KnowledgeNode[]> {
    const response = await api.get(`/graphs/nodes/${nodeId}/recommendations`, {
      params: { limit },
    })
    return response.data
  },

  /** 获取认知目标 */
  async getCognitiveGoals(nodeId: string, includeAvg = false): Promise<CognitiveGoal> {
    const response = await api.get(`/graphs/nodes/${nodeId}/cognitive`, {
      params: { include_avg: includeAvg },
    })
    return response.data
  },

  /** 创建知识节点 */
  async createNode(data: { id?: string; name: string; subject: string; description?: string }): Promise<KnowledgeNode> {
    const response = await api.post('/graphs/nodes', null, { params: data })
    return response.data
  },

  /** 删除知识节点及其图谱关系 */
  async deleteNode(nodeId: string): Promise<void> {
    await api.delete(`/graphs/nodes/${nodeId}`)
  },

  /** 下载知识点导入模板（csv） */
  async downloadKnowledgeTemplate(subjectId: string): Promise<void> {
    const response = await api.get(`/graphs/subjects/${subjectId}/nodes/import/template`, {
      responseType: 'blob',
    })
    const raw: BlobPart = (response as any)?.data ?? (response as any)
    const blob = raw instanceof Blob ? raw : new Blob([raw], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '知识点导入模板.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },

  /** 批量导入知识点（csv / xlsx） */
  async importKnowledgeNodes(subjectId: string, file: File): Promise<KnowledgeImportResult> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post(`/graphs/subjects/${subjectId}/nodes/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
    return response.data as KnowledgeImportResult
  },

  /** 更新知识节点 */
  async updateNode(nodeId: string, data: Record<string, unknown>): Promise<KnowledgeNode> {
    const response = await api.put(`/graphs/nodes/${nodeId}`, null, { params: data })
    return response.data
  },

  /** 创建节点关系 */
  async createRelationship(fromId: string, toId: string, relType = 'RELATED', label?: string): Promise<unknown> {
    const response = await api.post(`/graphs/nodes/${fromId}/link/${toId}`, null, {
      params: { rel_type: relType, label },
    })
    return response.data
  },

  /** 删除节点关系 */
  async deleteRelationship(fromId: string, toId: string, relType = 'RELATED'): Promise<void> {
    await api.delete(`/graphs/nodes/${fromId}/link/${toId}`, {
      params: { rel_type: relType },
    })
  },

  /** 搜索知识节点 */
  async searchNodes(q: string, subject?: string, limit = 20): Promise<KnowledgeNode[]> {
    const response = await api.get('/graphs/search', {
      params: { q, subject, limit },
    })
    return response.data
  },

  // ========== Misconception API ==========

  /** 获取节点误解标注列表 */
  async getMisconceptions(nodeId: string): Promise<Misconception[]> {
    const response = await api.get(`/graphs/nodes/${nodeId}/misconceptions`)
    return response.data
  },

  /** 教师添加误解标注 */
  async addMisconception(nodeId: string, data: MisconceptionInput): Promise<Misconception> {
    const response = await api.post(`/graphs/nodes/${nodeId}/misconceptions`, data)
    return response.data
  },

  /** 教师编辑误解标注 */
  async updateMisconception(nodeId: string, mcId: string, data: Partial<MisconceptionInput>): Promise<Misconception> {
    const response = await api.put(`/graphs/nodes/${nodeId}/misconceptions/${mcId}`, data)
    return response.data
  },

  /** 教师删除误解标注 */
  async deleteMisconception(nodeId: string, mcId: string): Promise<void> {
    await api.delete(`/graphs/nodes/${nodeId}/misconceptions/${mcId}`)
  },

  /** AI辅助标注建议 */
  async suggestMisconceptions(nodeId: string): Promise<AutoSuggestResponse> {
    const response = await api.post(`/graphs/nodes/${nodeId}/misconceptions/auto-suggest`)
    return response.data
  },

  // ========== 任务 API ==========

  /** 获取节点关联任务 */
  async getNodeTasks(nodeId: string): Promise<NodeTask[]> {
    const response = await api.get(`/graphs/nodes/${nodeId}/tasks`)
    return response.data
  },

  /** 获取学科节点及其直接知识点组成的完整层级图 */
  async getSubjectGraph(subjectId: string): Promise<NeighborData> {
    const response = await api.get(`/graphs/subjects/${subjectId}/graph`)
    return response.data
  },

  /** Submit a graph edit. Teacher/admin edits apply immediately; student edits await review. */
  async submitChange(
    nodeId: string,
    changeType: GraphChangeType,
    payload: Record<string, unknown>,
  ): Promise<GraphChangeResult> {
    const response = await api.post(`/graphs/nodes/${nodeId}/changes`, {
      change_type: changeType,
      payload,
    })
    return response.data
  },

  async getChangeRequests(
    nodeId?: string,
    status: 'pending' | 'approved' | 'rejected' = 'pending',
  ): Promise<GraphChangeRequest[]> {
    const response = await api.get('/graphs/change-requests', {
      params: { node_id: nodeId, status },
    })
    return response.data
  },

  async reviewChange(requestId: string, approved: boolean, comment?: string): Promise<void> {
    await api.post(`/graphs/change-requests/${requestId}/review`, { approved, comment })
  },

  async createNodeTask(
    nodeId: string,
    data: { name: string; description?: string; type: NodeTask['type']; due_date?: string },
  ): Promise<NodeTask> {
    const response = await api.post(`/graphs/nodes/${nodeId}/tasks`, data)
    return response.data
  },

  // ========== 跨学科图谱 API ==========

  /** 获取跨学科关联图谱 */
  async getCrossSubjectGraph(subjects: string[], minStrength = 0.0, maxNodes = 100): Promise<CrossSubjectResponse> {
    const response = await api.get('/graphs/cross-subject', {
      params: {
        subjects: subjects.join(','),
        min_strength: minStrength,
        max_nodes: maxNodes,
      },
    })
    return response.data
  },
}
