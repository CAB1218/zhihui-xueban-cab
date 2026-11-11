/**
 * AI4Edu Agent API Service
 * 封装所有AI智能体相关的API调用
 * 新增: 多模型列表、场景预设、引用来源、上下文摘要
 */
import api from './api'

// ============ 类型定义 ============

export interface AgentSession {
  id: string
  agent_type: string
  title: string
  scene_type?: string
  model_name?: string
  system_prompt?: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface AgentMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  model_name?: string
  created_at: string
  metadata?: Record<string, unknown>
}

interface AgentSessionDetail extends AgentSession {
  messages: AgentMessage[]
}

interface SessionListItem extends AgentSession {
  last_message_at?: string
}

export interface AgentTypeInfo {
  agent_type: string
  name: string
  description: string
  icon?: string
  supported_features?: string[]
}

export interface CreateSessionParams {
  agent_type?: string
  title?: string
  scene_type?: string
  course_id?: number
  model_name?: string
}

export interface SendMessageParams {
  content: string
  attachments?: string[]
}

export interface PaginatedSessions {
  items: AgentSession[]
  total: number
  page: number
  page_size: number
}

/** 模型信息 */
export interface ModelInfo {
  provider: string
  model: string
  status: string
  is_default: boolean
  is_configured?: boolean
}

/** 服务商配置（AI 对话 → 模型配置），Key 只回显掩码 */
export interface ModelProviderConfig {
  provider: string
  label: string
  key_url: string
  hint: string
  api_base: string
  model_name: string
  has_key: boolean
  key_masked: string
  configured: boolean
  source: 'page' | 'env' | 'none'
  editable_key: boolean
  env_key_masked: string
  last_test_ok: boolean | null
  last_test_message: string | null
  last_test_at: string | null
}

export interface ModelConfigResponse {
  providers: ModelProviderConfig[]
  any_configured: boolean
  can_edit: boolean
}

export interface ModelConfigUpdate {
  api_key?: string
  api_base?: string
  model_name?: string
  clear_key?: boolean
}

export interface ModelTestResult {
  ok: boolean
  message: string
  latency_ms: number | null
}

  /** 场景预设 */
export interface ScenePreset {
  scene_type: string
  name: string
  description: string
  icon: string
  preferred_model: string
  default_agent_type: string
}

/** 引用来源 */
export interface Citation {
  type: string
  title: string
  source_url: string
  teacher_name?: string
}

/** 上下文摘要 */
export interface ContextSummary {
  notes_count: number
  resources_count: number
  graph_nodes_count: number
  teacher_methods_count: number
}

/** 会话上下文响应 */
export interface SessionContextResponse {
  notes: Array<{ id: number; title: string; excerpt: string }>
  resources: Array<{ id: number; title: string; resource_type: string }>
  graph_nodes: Array<{ id: string; name: string }>
  teacher_methods: Array<{ id: number; title: string; teacher_name: string }>
  citations: Citation[]
  summary: ContextSummary
}

/** 发送消息完整响应 */
export interface SendMessageResponse {
  user_message: { id: number; role: string; content: string }
  assistant_message: { id: number; role: string; content: string; model_name: string }
  citations: Citation[]
  context_summary: ContextSummary
  model_used: string
  model_fallback: boolean
  detected_intent?: string
  agent_type?: string
}

// ============ v2 新增类型 ============

/** 模型负载均衡状态 */
export interface ModelBalancerProvider {
  provider: string
  model_name: string
  is_available: boolean
  is_configured: boolean
  avg_latency_ms: number
  success_rate: number
  failure_count: number
  last_check_time: number
}

/** 模型负载均衡响应 */
export interface ModelBalancerStatus {
  providers: ModelBalancerProvider[]
  current_strategy: string
  recommended_model: string | null
}

/** 课堂记录 */
export interface ClassroomRecord {
  id: number
  classroom_id: number
  course_id: number
  record_type: string
  status: string
  transcript?: string
  segments?: Array<{ text: string; start: number; end: number }>
  knowledge_points?: string[]
  provider?: string
  error_msg?: string
  file_url?: string
  created_at?: string
  updated_at?: string
}

/** 导出记录 */
export interface ExportRecord {
  id: number
  session_id: number
  export_format: string
  status: string
  file_size: number
  error_msg?: string
  created_at?: string
  completed_at?: string
  expired_at?: string
}

/** 导出下载链接 */
export interface ExportDownload {
  download_url: string
  expired_at: string
}

// ============ API 方法 ============

export const agentApi = {
  /** 获取会话列表 */
  async listSessions(params?: {
    page?: number
    page_size?: number
    agent_type?: string
  }): Promise<PaginatedSessions> {
    const response = await api.get('/agents/sessions', { params })
    const data = response.data as PaginatedSessions
    return {
      ...data,
      items: data.items.map((session: SessionListItem) => ({
        ...session,
        updated_at: session.updated_at ?? session.last_message_at ?? session.created_at,
      })),
    }
  },

  /** 创建新会话 */
  async createSession(params: CreateSessionParams): Promise<AgentSession> {
    const response = await api.post('/agents/sessions', params)
    const session = response.data as AgentSession
    return {
      ...session,
      message_count: session.message_count ?? 0,
      updated_at: session.updated_at ?? session.created_at,
    }
  },

  /** 获取会话详情 */
  async getSession(sessionId: string): Promise<AgentSessionDetail> {
    const response = await api.get(`/agents/sessions/${sessionId}`)
    return response.data as AgentSessionDetail
  },

  /** 发送消息 */
  async sendMessage(sessionId: string, params: SendMessageParams): Promise<SendMessageResponse> {
    const response = await api.post(`/agents/sessions/${sessionId}/messages`, params, { timeout: 120000 })
    return response.data as SendMessageResponse
  },

  /** 删除会话 */
  async deleteSession(sessionId: string): Promise<void> {
    await api.delete(`/agents/sessions/${sessionId}`)
  },

  /** 获取Agent类型列表 */
  async listAgentTypes(): Promise<AgentTypeInfo[]> {
    const response = await api.get('/agents/types')
    return response.data as AgentTypeInfo[]
  },

  /** 获取可用模型列表 */
  async listModels(): Promise<ModelInfo[]> {
    const response = await api.get('/agents/models')
    return response.data as ModelInfo[]
  },

  // ============ 模型配置（AI 对话 → 模型配置） ============

  /** 查看三家服务商的当前配置（Key 只返回掩码） */
  async getModelConfig(): Promise<ModelConfigResponse> {
    const res: any = await api.get('/agents/models/config')
    return (res?.data ?? res) as ModelConfigResponse
  },

  /** 保存配置（填写 API Key / Base / 模型名），保存后立即生效 */
  async saveModelConfig(provider: string, payload: ModelConfigUpdate): Promise<ModelConfigResponse> {
    const res: any = await api.put(`/agents/models/config/${provider}`, payload)
    return (res?.data ?? res) as ModelConfigResponse
  },

  /** 清除页面配置，回退到 backend/.env */
  async resetModelConfig(provider: string): Promise<ModelConfigResponse> {
    const res: any = await api.delete(`/agents/models/config/${provider}`)
    return (res?.data ?? res) as ModelConfigResponse
  },

  /** 测试连通性：传了 api_key/base/model 就用临时值测试，否则测已保存的配置 */
  async testModelConfig(provider: string, payload: ModelConfigUpdate = {}): Promise<ModelTestResult> {
    const res: any = await api.post(`/agents/models/config/${provider}/test`, payload, {
      timeout: 45000,
    })
    return (res?.data ?? res) as ModelTestResult
  },

  /** 获取场景预设列表 */
  async listScenes(): Promise<ScenePreset[]> {
    const response = await api.get('/agents/scenes')
    return response.data as ScenePreset[]
  },

  /** 获取会话上下文资源 */
  async getSessionContext(sessionId: string): Promise<SessionContextResponse> {
    const response = await api.get(`/agents/sessions/${sessionId}/context`)
    return response.data as SessionContextResponse
  },

  /** 获取WebSocket连接URL */
  getStreamUrl(sessionId: string): string {
    // 优先使用显式配置；否则根据当前页面协议/主机动态构造
    let baseUrl: string
    if (import.meta.env.VITE_WS_BASE_URL) {
      baseUrl = import.meta.env.VITE_WS_BASE_URL
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      baseUrl = `${protocol}//${window.location.host}`
    }
    const token = localStorage.getItem('access_token') || ''
    return `${baseUrl}/api/v1/agents/ws/${sessionId}?token=${token}`
  },

  // ============ v2 新增: 模型负载均衡 ============

  /** 获取模型负载均衡状态 */
  async getModelBalancerStatus(): Promise<ModelBalancerStatus> {
    const response = await api.get('/agents/models/balancer')
    return response.data as ModelBalancerStatus
  },

  // ============ v2 新增: 课堂记录 ============

  /** 获取课堂记录列表 */
  async listClassroomRecords(params?: {
    classroom_id?: number
    course_id?: number
    record_type?: string
    status_filter?: string
    page?: number
    page_size?: number
  }): Promise<{ items: ClassroomRecord[]; total: number; page: number; page_size: number }> {
    const response = await api.get('/agents/classroom-records', { params })
    return response.data as { items: ClassroomRecord[]; total: number; page: number; page_size: number }
  },

  /** 获取课堂记录详情 */
  async getClassroomRecord(recordId: number): Promise<ClassroomRecord> {
    const response = await api.get(`/agents/classroom-records/${recordId}`)
    return response.data as ClassroomRecord
  },

  /** 重新处理课堂记录 */
  async reprocessClassroomRecord(recordId: number): Promise<void> {
    await api.post(`/agents/classroom-records/${recordId}/reprocess`)
  },

  /** 删除课堂记录 */
  async deleteClassroomRecord(recordId: number): Promise<void> {
    await api.delete(`/agents/classroom-records/${recordId}`)
  },

  // ============ v2 新增: 对话导出 ============

  /** 创建导出任务 */
  async createExport(sessionId: number, exportFormat: string): Promise<ExportRecord> {
    const response = await api.post(`/agents/sessions/${sessionId}/exports`, {
      export_format: exportFormat,
    })
    return response.data as ExportRecord
  },

  /** 获取会话的导出列表 */
  async listExports(
    sessionId: number,
    page: number = 1,
    pageSize: number = 20,
  ): Promise<{ items: ExportRecord[]; total: number; page: number; page_size: number }> {
    const response = await api.get(`/agents/sessions/${sessionId}/exports`, {
      params: { page, page_size: pageSize },
    })
    return response.data as { items: ExportRecord[]; total: number; page: number; page_size: number }
  },

  /** 获取导出详情 */
  async getExport(exportId: number): Promise<ExportRecord> {
    const response = await api.get(`/agents/exports/${exportId}`)
    return response.data as ExportRecord
  },

  /** 获取导出下载链接 */
  async downloadExport(exportId: number): Promise<ExportDownload> {
    const response = await api.get(`/agents/exports/${exportId}/download`)
    return response.data as ExportDownload
  },
}
