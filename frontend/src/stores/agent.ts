/**
 * 智慧学伴 Agent Store
 * 管理AI会话列表、当前会话、消息流、Agent类型、流式消息接收
 * 新增: 场景预设、模型列表、引用来源、上下文摘要
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  agentApi,
  type AgentSession,
  type AgentMessage,
  type AgentTypeInfo,
  type ScenePreset,
  type ModelInfo,
  type Citation,
  type ContextSummary,
  type ExportRecord,
} from '@/services/agent'
import { ElMessage } from 'element-plus'

export const useAgentStore = defineStore('agent', () => {
  // ============ State ============

  /** 会话列表 */
  const sessions = ref<AgentSession[]>([])
  /** 当前选中会话 */
  const currentSession = ref<AgentSession | null>(null)
  /** 当前会话消息列表 */
  const messages = ref<AgentMessage[]>([])
  /** Agent类型列表 */
  const agentTypes = ref<AgentTypeInfo[]>([])
  /** 是否正在流式接收 */
  const isStreaming = ref<boolean>(false)
  /** 流式消息内容（逐字追加） */
  const streamingContent = ref<string>('')
  /** 加载状态 */
  const loading = ref<boolean>(false)
  /** 消息加载状态 */
  const messagesLoading = ref<boolean>(false)
  /** 会话总数 */
  const totalSessions = ref<number>(0)
  /** 当前页码 */
  const currentPage = ref<number>(1)
  /** 场景预设列表 */
  const scenes = ref<ScenePreset[]>([])
  /** 模型列表 */
  const models = ref<ModelInfo[]>([])
  /** 当前场景 */
  const currentScene = ref<ScenePreset | null>(null)
  /** 当前上下文摘要（从最近 AI 消息 metadata 获取） */
  const currentContextSummary = ref<ContextSummary | null>(null)
  /** v2: 当前会话的导出记录列表 */
  const exportRecords = ref<ExportRecord[]>([])
  /** v2: 导出加载状态 */
  const exportLoading = ref<boolean>(false)
  /** WebSocket实例 */
  let wsConnection: WebSocket | null = null

  // ============ Getters ============

  /** 当前Agent类型 */
  const currentAgentType = computed<AgentTypeInfo | null>(() => {
    if (!currentSession.value) return null
    return agentTypes.value.find((t) => t.agent_type === currentSession.value!.agent_type) ?? null
  })

  /** 是否有活跃会话 */
  const hasActiveSession = computed<boolean>(() => currentSession.value !== null)

  /** 排序后的消息列表（按时间升序） */
  const sortedMessages = computed<AgentMessage[]>(() => {
    return [...messages.value].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    )
  })

  /** 可用模型数量 */
  const availableModelCount = computed<number>(() => {
    return models.value.filter((m) => m.status === 'available').length
  })

  // ============ Actions ============

  /**
   * 获取会话列表
   * @param page 页码
   * @param pageSize 每页数量
   * @param agentType Agent类型筛选
   */
  async function fetchSessions(page: number = 1, pageSize: number = 20, agentType?: string): Promise<void> {
    loading.value = true
    try {
      const response = await agentApi.listSessions({
        page,
        page_size: pageSize,
        agent_type: agentType,
      })
      sessions.value = response.items
      totalSessions.value = response.total
      currentPage.value = page
    } catch (error) {
      console.error('获取会话列表失败:', error)
      ElMessage.error('获取会话列表失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建新会话
   * @param agentType Agent类型
   * @param title 会话标题
   */
  async function createSession(agentType: string, title?: string): Promise<AgentSession | null> {
    try {
      const session = await agentApi.createSession({ agent_type: agentType, title })
      sessions.value.unshift(session)
      currentSession.value = session
      messages.value = []
      return session
    } catch (error) {
      console.error('创建会话失败:', error)
      ElMessage.error('创建会话失败')
      return null
    }
  }

  /**
   * 创建场景会话（新增）
   * @param sceneType 场景类型
   * @param courseId 课程ID（可选）
   * @param title 会话标题（可选）
   */
  async function createSceneSession(
    sceneType: string,
    courseId?: number,
    title?: string,
  ): Promise<AgentSession | null> {
    try {
      // 设置当前场景
      currentScene.value = scenes.value.find((s) => s.scene_type === sceneType) || null
      const session = await agentApi.createSession({
        scene_type: sceneType,
        course_id: courseId,
        title: title || `${currentScene.value?.name || 'AI'}会话`,
      })
      sessions.value.unshift(session)
      currentSession.value = session
      messages.value = []
      return session
    } catch (error) {
      console.error('创建场景会话失败:', error)
      ElMessage.error('创建场景会话失败')
      return null
    }
  }

  /**
   * 选择会话
   * @param sessionId 会话ID
   */
  async function selectSession(sessionId: string): Promise<void> {
    const session = sessions.value.find((s) => String(s.id) === String(sessionId))
    if (!session) {
      try {
        currentSession.value = await agentApi.getSession(sessionId)
      } catch (error) {
        console.error('获取会话详情失败:', error)
        return
      }
    } else {
      currentSession.value = session
    }
    // 设置当前场景
    if (currentSession.value?.scene_type) {
      currentScene.value = scenes.value.find(
        (s) => s.scene_type === currentSession.value!.scene_type,
      ) || null
    }
    // 加载消息历史
    await fetchMessages(sessionId)
    // 断开旧WebSocket
    disconnectStream()
  }

  /**
   * 获取会话消息列表
   * @param sessionId 会话ID
   */
  async function fetchMessages(sessionId: string): Promise<void> {
    messagesLoading.value = true
    try {
      const sessionData = await agentApi.getSession(sessionId)
      messages.value = sessionData.messages ?? []
    } catch (error) {
      console.error('获取消息列表失败:', error)
      messages.value = []
    } finally {
      messagesLoading.value = false
    }
  }

  /**
   * 发送消息（HTTP方式，非流式）
   * @param content 消息内容
   */
  async function sendMessage(content: string): Promise<void> {
    if (!currentSession.value) {
      ElMessage.warning('请先选择或创建会话')
      return
    }

    // 添加用户消息到列表
    const userMessage: AgentMessage = {
      id: `temp_${Date.now()}`,
      session_id: currentSession.value.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    messages.value.push(userMessage)
    isStreaming.value = true

    try {
      const result = await agentApi.sendMessage(currentSession.value.id, { content })
      // 添加 AI 消息（含 metadata）
      const assistantMessage: AgentMessage = {
        id: String(result.assistant_message.id),
        session_id: currentSession.value.id,
        role: 'assistant',
        content: result.assistant_message.content,
        model_name: result.assistant_message.model_name,
        created_at: new Date().toISOString(),
        metadata: {
          citations: result.citations,
          context_summary: result.context_summary,
          model_used: result.model_used,
          model_fallback: result.model_fallback,
        },
      }
      messages.value.push(assistantMessage)

      // 更新上下文摘要
      currentContextSummary.value = result.context_summary
    } catch (error) {
      console.error('发送消息失败:', error)
      ElMessage.error('发送消息失败')
    } finally {
      isStreaming.value = false
    }
  }

  /**
   * 流式发送消息（WebSocket）
   * @param content 消息内容
   */
  async function streamMessage(content: string): Promise<void> {
    if (!currentSession.value) {
      ElMessage.warning('请先选择或创建会话')
      return
    }

    // 添加用户消息
    const userMessage: AgentMessage = {
      id: `temp_${Date.now()}`,
      session_id: currentSession.value.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    messages.value.push(userMessage)

    // 建立WebSocket连接
    isStreaming.value = true
    streamingContent.value = ''

    const wsUrl = agentApi.getStreamUrl(currentSession.value.id)
    wsConnection = new WebSocket(wsUrl)

    wsConnection.onopen = () => {
      // 发送消息
      wsConnection!.send(
        JSON.stringify({
          type: 'chat',
          content,
          session_id: currentSession.value!.id,
        })
      )
    }

    wsConnection.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string)

        if (data.type === 'context') {
          // 接收上下文摘要
          currentContextSummary.value = data.summary as ContextSummary
        } else if (data.type === 'chunk' || data.type === 'token') {
          // 流式追加内容
          streamingContent.value += data.content
        } else if (data.type === 'done' || data.type === 'message_end') {
          // 消息结束，将流式内容转为正式消息
          const citations: Citation[] = data.citations || []
          const contextSummary: ContextSummary | null = data.context_summary || data.metadata?.context_summary || null
          const modelUsed: string = data.model_used || data.metadata?.model_used || ''
          const modelFallback: boolean = data.model_fallback || data.metadata?.model_fallback || false

          const assistantMessage: AgentMessage = {
            id: data.message_id || `msg_${Date.now()}`,
            session_id: currentSession.value!.id,
            role: 'assistant',
            content: streamingContent.value,
            model_name: modelUsed,
            created_at: new Date().toISOString(),
            metadata: {
              citations,
              context_summary: contextSummary,
              model_used: modelUsed,
              model_fallback: modelFallback,
            },
          }
          messages.value.push(assistantMessage)
          streamingContent.value = ''
          isStreaming.value = false

          // 更新上下文摘要
          if (contextSummary) {
            currentContextSummary.value = contextSummary
          }
        } else if (data.type === 'error') {
          ElMessage.error(data.message || 'AI回复出错')
          isStreaming.value = false
          streamingContent.value = ''
        }
      } catch (e) {
        console.error('解析WebSocket消息失败:', e)
      }
    }

    wsConnection.onerror = (error) => {
      console.error('WebSocket连接错误:', error)
      ElMessage.error('连接失败，请稍后重试')
      isStreaming.value = false
      streamingContent.value = ''
    }

    wsConnection.onclose = () => {
      isStreaming.value = false
    }
  }

  /**
   * 断开WebSocket连接
   */
  function disconnectStream(): void {
    if (wsConnection) {
      wsConnection.close()
      wsConnection = null
    }
    isStreaming.value = false
    streamingContent.value = ''
  }

  /**
   * 获取Agent类型列表
   */
  async function fetchAgentTypes(): Promise<void> {
    try {
      agentTypes.value = await agentApi.listAgentTypes()
    } catch (error) {
      console.error('获取Agent类型失败:', error)
    }
  }

  /**
   * 获取场景预设列表（新增）
   */
  async function fetchScenes(): Promise<void> {
    try {
      scenes.value = await agentApi.listScenes()
    } catch (error) {
      console.error('获取场景列表失败:', error)
    }
  }

  /**
   * 获取模型列表（新增）
   */
  async function fetchModels(): Promise<void> {
    try {
      models.value = await agentApi.listModels()
    } catch (error) {
      console.error('获取模型列表失败:', error)
    }
  }

  /**
   * 删除会话
   * @param sessionId 会话ID
   */
  async function deleteSession(sessionId: string): Promise<void> {
    try {
      await agentApi.deleteSession(sessionId)
      sessions.value = sessions.value.filter((s) => String(s.id) !== String(sessionId))
      if (currentSession.value?.id === sessionId) {
        currentSession.value = null
        messages.value = []
        disconnectStream()
      }
      ElMessage.success('会话已删除')
    } catch (error) {
      console.error('删除会话失败:', error)
      ElMessage.error('删除会话失败')
    }
  }

  /**
   * 清除当前会话状态
   */
  function clearCurrentSession(): void {
    disconnectStream()
    currentSession.value = null
    messages.value = []
    streamingContent.value = ''
    currentContextSummary.value = null
    exportRecords.value = []
  }

  // ============ v2 新增: 对话导出 ============

  /**
   * 创建导出任务
   * @param exportFormat 导出格式: pdf / markdown
   */
  async function createExport(exportFormat: string): Promise<ExportRecord | null> {
    if (!currentSession.value) {
      ElMessage.warning('请先选择或创建会话')
      return null
    }
    exportLoading.value = true
    try {
      const record = await agentApi.createExport(
        Number(currentSession.value.id),
        exportFormat,
      )
      exportRecords.value.unshift(record)
      ElMessage.success('导出任务已创建，请稍后查看状态')
      return record
    } catch (error) {
      console.error('创建导出任务失败:', error)
      ElMessage.error('创建导出任务失败')
      return null
    } finally {
      exportLoading.value = false
    }
  }

  /**
   * 获取当前会话的导出列表
   */
  async function fetchExportRecords(): Promise<void> {
    if (!currentSession.value) return
    try {
      const result = await agentApi.listExports(Number(currentSession.value.id))
      exportRecords.value = result.items
    } catch (error) {
      console.error('获取导出列表失败:', error)
    }
  }

  /**
   * 轮询导出状态（直到 completed 或 failed）
   * @param exportId 导出 ID
   * @param maxAttempts 最大轮询次数
   */
  async function pollExportStatus(
    exportId: number,
    maxAttempts: number = 30,
  ): Promise<ExportRecord | null> {
    const interval = 2000 // 2 秒
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const record = await agentApi.getExport(exportId)
        // 更新列表中的记录
        const idx = exportRecords.value.findIndex((r) => r.id === exportId)
        if (idx >= 0) {
          exportRecords.value[idx] = record
        }
        if (record.status === 'completed' || record.status === 'failed') {
          return record
        }
      } catch (error) {
        console.error('轮询导出状态失败:', error)
      }
      await new Promise((resolve) => setTimeout(resolve, interval))
    }
    return null
  }

  /**
   * 下载导出文件
   * @param exportId 导出 ID
   */
  async function downloadExport(exportId: number): Promise<void> {
    try {
      const result = await agentApi.downloadExport(exportId)
      // 在新窗口打开下载链接
      window.open(result.download_url, '_blank')
    } catch (error) {
      console.error('获取下载链接失败:', error)
      ElMessage.error('获取下载链接失败，请确认导出已完成')
    }
  }

  return {
    // State
    sessions,
    currentSession,
    messages,
    agentTypes,
    isStreaming,
    streamingContent,
    loading,
    messagesLoading,
    totalSessions,
    currentPage,
    scenes,
    models,
    currentScene,
    currentContextSummary,
    exportRecords,
    exportLoading,
    // Getters
    currentAgentType,
    hasActiveSession,
    sortedMessages,
    availableModelCount,
    // Actions
    fetchSessions,
    createSession,
    createSceneSession,
    selectSession,
    fetchMessages,
    sendMessage,
    streamMessage,
    disconnectStream,
    fetchAgentTypes,
    fetchScenes,
    fetchModels,
    deleteSession,
    clearCurrentSession,
    // v2 导出
    createExport,
    fetchExportRecords,
    pollExportStatus,
    downloadExport,
  }
})
