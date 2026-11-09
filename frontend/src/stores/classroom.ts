/**
 * AI4Edu 课堂 Store
 * 管理课堂状态、参与者、投票、WebSocket连接
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { classroomApi, type ClassroomInfo, type ClassroomParticipant, type PollItem, type ClassroomMessage, type PollResult } from '@/services/classroom'
import { ElMessage } from 'element-plus'

export const useClassroomStore = defineStore('classroom', () => {
  // ============ State ============

  /** 当前课堂 */
  const currentClassroom = ref<ClassroomInfo | null>(null)
  /** 参与者列表 */
  const participants = ref<ClassroomParticipant[]>([])
  /** 投票列表 */
  const polls = ref<PollItem[]>([])
  /** 课堂消息 */
  const messages = ref<ClassroomMessage[]>([])
  /** 是否举手 */
  const handRaised = ref<boolean>(false)
  /** WebSocket是否已连接 */
  const isConnected = ref<boolean>(false)
  /** 加载状态 */
  const loading = ref<boolean>(false)
  /** 当前投票结果 */
  const currentPollResult = ref<PollResult | null>(null)
  /** WebSocket实例 */
  let wsConnection: WebSocket | null = null

  // ============ Getters ============

  /** 是否在课堂中 */
  const isInClassroom = computed<boolean>(() => currentClassroom.value !== null)

  /** 课堂是否活跃 */
  const isClassroomActive = computed<boolean>(() => currentClassroom.value?.status === 'active')

  /** 在线参与者数量 */
  const onlineParticipantCount = computed<number>(() => participants.value.filter((p) => p.is_online).length)

  /** 举手的学生列表 */
  const raisedHandStudents = computed<ClassroomParticipant[]>(() => participants.value.filter((p) => p.hand_raised))

  /** 活跃投票 */
  const activePoll = computed<PollItem | null>(() => polls.value.find((p) => p.is_active) ?? null)

  /** 排序后的消息列表 */
  const sortedMessages = computed<ClassroomMessage[]>(() => {
    return [...messages.value].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    )
  })

  // ============ Actions ============

  /**
   * 创建课堂
   * @param name 课堂名称
   * @param courseId 课程ID
   */
  async function createClassroom(name: string, courseId?: number): Promise<ClassroomInfo | null> {
    loading.value = true
    try {
      const classroom = await classroomApi.createClassroom({ title: name, course_id: courseId })
      currentClassroom.value = classroom
      ElMessage.success('课堂创建成功')
      return classroom
    } catch (error) {
      console.error('创建课堂失败:', error)
      ElMessage.error('创建课堂失败')
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * 加入课堂
   * @param classroomId 课堂ID
   */
  async function joinClassroom(classroomId: string): Promise<void> {
    loading.value = true
    try {
      const classroom = await classroomApi.joinClassroom(classroomId)
      currentClassroom.value = classroom
      // 连接WebSocket
      connectWS(classroomId)
      ElMessage.success('已加入课堂')
    } catch (error) {
      console.error('加入课堂失败:', error)
      ElMessage.error('加入课堂失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 离开课堂
   */
  async function leaveClassroom(): Promise<void> {
    if (!currentClassroom.value) return

    try {
      await classroomApi.leaveClassroom(currentClassroom.value.id)
      disconnectWS()
      currentClassroom.value = null
      participants.value = []
      polls.value = []
      messages.value = []
      handRaised.value = false
      currentPollResult.value = null
      ElMessage.success('已离开课堂')
    } catch (error) {
      console.error('离开课堂失败:', error)
      ElMessage.error('离开课堂失败')
    }
  }

  /**
   * 举手/放下手
   */
  async function raiseHand(): Promise<void> {
    if (!currentClassroom.value) return

    try {
      await classroomApi.raiseHand(currentClassroom.value.id)
      handRaised.value = !handRaised.value
      ElMessage.success(handRaised.value ? '已举手' : '已放下')
    } catch (error) {
      console.error('举手操作失败:', error)
      ElMessage.error('操作失败')
    }
  }

  /**
   * 创建投票
   * @param question 问题
   * @param options 选项列表
   */
  async function createPoll(question: string, options: string[]): Promise<void> {
    if (!currentClassroom.value) return

    try {
      const poll = await classroomApi.createPoll(currentClassroom.value.id, { question, options })
      polls.value.push(poll)
      ElMessage.success('投票已创建')
    } catch (error) {
      console.error('创建投票失败:', error)
      ElMessage.error('创建投票失败')
    }
  }

  /**
   * 参与投票
   * @param pollId 投票ID
   * @param optionIndex 选项索引
   */
  async function votePoll(pollId: string, optionIndex: number): Promise<void> {
    if (!currentClassroom.value) return

    try {
      await classroomApi.votePoll(currentClassroom.value.id, pollId, { option_index: optionIndex })
      ElMessage.success('投票成功')
      // 获取最新结果
      await fetchPollResult(pollId)
    } catch (error) {
      console.error('投票失败:', error)
      ElMessage.error('投票失败')
    }
  }

  /**
   * 获取投票结果
   * @param pollId 投票ID
   */
  async function fetchPollResult(pollId: string): Promise<void> {
    if (!currentClassroom.value) return

    try {
      currentPollResult.value = await classroomApi.getPollResult(currentClassroom.value.id, pollId)
    } catch (error) {
      console.error('获取投票结果失败:', error)
    }
  }

  /**
   * 连接课堂WebSocket
   * @param classroomId 课堂ID
   */
  function connectWS(classroomId: string): void {
    const wsUrl = classroomApi.getWebSocketUrl(classroomId)
    wsConnection = new WebSocket(wsUrl)

    wsConnection.onopen = () => {
      isConnected.value = true
    }

    wsConnection.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string)

        switch (data.type) {
          case 'participant_update':
            participants.value = data.participants as ClassroomParticipant[]
            break
          case 'message':
            messages.value.push(data.message as ClassroomMessage)
            break
          case 'poll_created':
            polls.value.push(data.poll as PollItem)
            break
          case 'poll_result':
            currentPollResult.value = data.result as PollResult
            break
          case 'hand_raise':
            {
              const participant = participants.value.find((p) => p.id === data.user_id)
              if (participant) {
                participant.hand_raised = data.raised as boolean
              }
            }
            break
          case 'classroom_ended':
            currentClassroom.value!.status = 'ended'
            disconnectWS()
            ElMessage.info('课堂已结束')
            break
          default:
            break
        }
      } catch (e) {
        console.error('解析WebSocket消息失败:', e)
      }
    }

    wsConnection.onerror = (error) => {
      console.error('课堂WebSocket连接错误:', error)
      isConnected.value = false
    }

    wsConnection.onclose = () => {
      isConnected.value = false
    }
  }

  /**
   * 断开课堂WebSocket
   */
  function disconnectWS(): void {
    if (wsConnection) {
      wsConnection.close()
      wsConnection = null
    }
    isConnected.value = false
  }

  /**
   * 发送课堂聊天消息
   * @param content 消息内容
   */
  function sendClassroomMessage(content: string): void {
    if (wsConnection && isConnected.value) {
      wsConnection.send(
        JSON.stringify({
          type: 'chat',
          content,
        })
      )
    }
  }

  /**
   * 清除课堂状态
   */
  function clearClassroom(): void {
    disconnectWS()
    currentClassroom.value = null
    participants.value = []
    polls.value = []
    messages.value = []
    handRaised.value = false
    currentPollResult.value = null
  }

  return {
    // State
    currentClassroom,
    participants,
    polls,
    messages,
    handRaised,
    isConnected,
    loading,
    currentPollResult,
    // Getters
    isInClassroom,
    isClassroomActive,
    onlineParticipantCount,
    raisedHandStudents,
    activePoll,
    sortedMessages,
    // Actions
    createClassroom,
    joinClassroom,
    leaveClassroom,
    raiseHand,
    createPoll,
    votePoll,
    fetchPollResult,
    connectWS,
    disconnectWS,
    sendClassroomMessage,
    clearClassroom,
  }
})
