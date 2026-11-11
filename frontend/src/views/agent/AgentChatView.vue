<template>
  <div class="agent-chat">
    <!-- 左侧会话列表 -->
    <div class="agent-chat__sidebar">
      <div class="agent-chat__sidebar-header">
        <h3>AI 助手</h3>
        <el-button type="primary" size="small" @click="handleNewSession">
          <el-icon><Plus /></el-icon> 新会话
        </el-button>
      </div>

      <!-- Agent类型选择 -->
      <div class="agent-chat__type-selector">
        <el-select v-model="selectedAgentType" placeholder="选择助手类型" size="small" @change="handleTypeChange">
          <el-option
            v-for="at in agentStore.agentTypes"
            :key="at.agent_type"
            :label="at.name"
            :value="at.agent_type"
          />
        </el-select>
      </div>

      <!-- 会话列表 -->
      <div class="agent-chat__session-list">
        <div
          v-for="session in agentStore.sessions"
          :key="session.id"
          :class="['agent-chat__session-item', { 'agent-chat__session-item--active': session.id === agentStore.currentSession?.id }]"
          @click="handleSelectSession(String(session.id))"
        >
          <div class="agent-chat__session-info">
            <span class="agent-chat__session-title">{{ session.title }}</span>
            <span class="agent-chat__session-meta">{{ formatTime(session.updated_at) }}</span>
          </div>
          <el-button
            type="danger"
            link
            size="small"
            @click.stop="handleDeleteSession(String(session.id))"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-empty v-if="agentStore.sessions.length === 0" description="暂无会话" :image-size="60" />
      </div>
    </div>

    <!-- 右侧对话区域 -->
    <div class="agent-chat__main">
      <!-- 顶部Agent信息 -->
      <div v-if="agentStore.currentAgentType || currentSceneName" class="agent-chat__header">
        <el-avatar :size="36" :style="{ backgroundColor: '#1976D2' }">
          <el-icon :size="20"><ChatDotRound /></el-icon>
        </el-avatar>
        <div class="agent-chat__header-info">
          <span class="agent-chat__header-name">
            {{ currentSceneName || agentStore.currentAgentType?.name || 'AI 对话' }}
          </span>
          <span class="agent-chat__header-desc">{{ agentStore.currentAgentType?.description || '智能学习助手' }}</span>
        </div>
        <!-- 模型选择器 -->
        <el-dropdown
          class="agent-chat__model-dropdown"
          trigger="click"
          @command="handleModelChange"
        >
          <div class="agent-chat__model-indicator" :title="modelTooltip">
            <span :class="['agent-chat__model-dot', modelDotClass]"></span>
            <span class="agent-chat__model-name">{{ currentModelName }}</span>
            <el-icon class="agent-chat__model-arrow"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="model in agentStore.models"
                :key="`${model.provider}-${model.model}`"
                :command="model.provider"
                :disabled="model.status !== 'available'"
              >
                <div class="agent-chat__model-option">
                  <span
                    :class="[
                      'agent-chat__model-option-dot',
                      model.status === 'available' ? 'agent-chat__model-option-dot--green' : 'agent-chat__model-option-dot--gray',
                    ]"
                  ></span>
                  <span class="agent-chat__model-option-name">{{ model.provider }} / {{ model.model }}</span>
                  <span class="agent-chat__model-option-status">{{ model.status === 'available' ? '可用' : '未配置' }}</span>
                </div>
              </el-dropdown-item>
              <el-dropdown-item divided command="__config">
                <div class="agent-chat__model-option">
                  <el-icon class="agent-chat__model-config-icon"><Setting /></el-icon>
                  <span class="agent-chat__model-option-name">模型配置…</span>
                  <span class="agent-chat__model-option-status">填 API Key</span>
                </div>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <!-- 导出按钮 -->
        <el-button
          type="primary"
          plain
          size="small"
          :icon="Download"
          @click="exportDialogVisible = true"
        >
          导出
        </el-button>
      </div>

      <!-- 消息列表 -->
      <div ref="messageContainerRef" class="agent-chat__messages">
        <div
          v-for="msg in agentStore.sortedMessages"
          :key="msg.id"
          :class="['agent-chat__message', `agent-chat__message--${msg.role}`]"
        >
          <el-avatar v-if="msg.role === 'assistant'" :size="32" :style="{ backgroundColor: '#1976D2' }">
            <el-icon :size="16"><ChatDotRound /></el-icon>
          </el-avatar>
          <div class="agent-chat__message-content">
            <div class="agent-chat__message-bubble" v-html="renderMarkdown(msg.content)"></div>
            <!-- 引用来源展示 -->
            <CitationList
              v-if="msg.role === 'assistant' && getMessageCitations(msg)"
              :citations="getMessageCitations(msg)!"
            />
            <span class="agent-chat__message-time">{{ formatTime(msg.created_at) }}</span>
          </div>
        </div>

        <!-- 流式消息显示 -->
        <div v-if="agentStore.isStreaming && agentStore.streamingContent" class="agent-chat__message agent-chat__message--assistant">
          <el-avatar :size="32" :style="{ backgroundColor: '#1976D2' }">
            <el-icon :size="16"><ChatDotRound /></el-icon>
          </el-avatar>
          <div class="agent-chat__message-content">
            <div class="agent-chat__message-bubble agent-chat__message-bubble--streaming">
              <span v-html="renderMarkdown(agentStore.streamingContent)"></span>
              <span class="agent-chat__cursor">|</span>
            </div>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="agentStore.isStreaming && !agentStore.streamingContent" class="agent-chat__message agent-chat__message--assistant">
          <el-avatar :size="32" :style="{ backgroundColor: '#1976D2' }">
            <el-icon :size="16"><ChatDotRound /></el-icon>
          </el-avatar>
          <div class="agent-chat__message-content">
            <div class="agent-chat__message-bubble agent-chat__message-bubble--loading">
              <span class="agent-chat__dot"></span>
              <span class="agent-chat__dot"></span>
              <span class="agent-chat__dot"></span>
            </div>
          </div>
        </div>

        <el-empty v-if="!agentStore.hasActiveSession" description="选择或创建一个会话开始对话" :image-size="100" />
      </div>

      <!-- 底部输入区 -->
      <div v-if="agentStore.hasActiveSession" class="agent-chat__input-area">
        <!-- 上下文标签 -->
        <ContextBadges :summary="agentStore.currentContextSummary" />
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          :placeholder="`输入消息，按 Enter 发送，Shift+Enter 换行...`"
          resize="none"
          :disabled="agentStore.isStreaming"
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button
          type="primary"
          :icon="Promotion"
          :loading="agentStore.isStreaming"
          :disabled="!inputMessage.trim()"
          @click="handleSend"
        >
          发送
        </el-button>
      </div>
    </div>

    <!-- 导出对话框 -->
    <ExportDialog v-model="exportDialogVisible" />
    <ModelConfigDialog v-model="modelConfigVisible" @changed="onModelConfigChanged" />
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu AI智能体对话页面
 * 左侧会话列表 + 右侧对话区域 + WebSocket流式消息
 */
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Promotion, Plus, Delete, ChatDotRound, Download, ArrowDown, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAgentStore } from '@/stores/agent'
import CitationList from './components/CitationList.vue'
import ContextBadges from './components/ContextBadges.vue'
import ModelConfigDialog from './components/ModelConfigDialog.vue'
import ExportDialog from '@/components/agent/ExportDialog.vue'
import type { Citation } from '@/services/agent'

const agentStore = useAgentStore()
const route = useRoute()

/** 模型配置对话框（填 DeepSeek 等 API Key） */
const modelConfigVisible = ref(false)

async function onModelConfigChanged(): Promise<void> {
  await agentStore.fetchModels()
}

const inputMessage = ref<string>('')
const selectedAgentType = ref<string>('general')
const preferredModel = ref<string>('')
const messageContainerRef = ref<HTMLElement | null>(null)
const exportDialogVisible = ref<boolean>(false)

/** 当前场景名称 */
const currentSceneName = computed<string>(() => {
  const sceneType = agentStore.currentSession?.scene_type
  if (!sceneType) return ''
  const scene = agentStore.scenes.find((s) => s.scene_type === sceneType)
  return scene ? scene.name : ''
})

/** 当前模型名称 */
const currentModelName = computed<string>(() => {
  if (preferredModel.value) return preferredModel.value
  const lastMsg = agentStore.messages[agentStore.messages.length - 1]
  if (lastMsg?.role === 'assistant' && (lastMsg as any).model_name) {
    return (lastMsg as any).model_name
  }
  return agentStore.currentSession?.model_name || 'AI'
})

/** 模型指示灯样式 */
const modelDotClass = computed<string>(() => {
  const count = agentStore.availableModelCount
  if (count >= 2) return 'agent-chat__model-dot--green'
  if (count === 1) return 'agent-chat__model-dot--yellow'
  return 'agent-chat__model-dot--red'
})

/** 模型 tooltip */
const modelTooltip = computed<string>(() => {
  const count = agentStore.availableModelCount
  if (count >= 2) return `${count} 个模型可用`
  if (count === 1) return `仅 ${count} 个模型可用，可能降级`
  return '无可用模型，点击这里选择「模型配置」填 API Key'
})

/** 从消息 metadata 中提取引用来源 */
function getMessageCitations(msg: any): Citation[] | null {
  if (!msg?.metadata?.citations) return null
  return msg.metadata.citations as Citation[]
}

/** 发送消息 */
async function handleSend(): Promise<void> {
  const content = inputMessage.value.trim()
  if (!content) return

  inputMessage.value = ''
  await agentStore.sendMessage(content)
  await scrollToBottom()
}

/** 选择会话 */
async function handleSelectSession(sessionId: string): Promise<void> {
  await agentStore.selectSession(sessionId)
  await scrollToBottom()
}

/** 创建新会话 */
async function handleNewSession(): Promise<void> {
  await agentStore.createSession(selectedAgentType.value)
  await scrollToBottom()
}

/** 删除会话 */
async function handleDeleteSession(sessionId: string): Promise<void> {
  try {
    await ElMessageBox.confirm('确定删除该会话？', '确认删除', { type: 'warning' })
    await agentStore.deleteSession(sessionId)
  } catch {
    // 用户取消
  }
}

/** 切换Agent类型 */
function handleTypeChange(): void {
  agentStore.fetchSessions(1, 20, selectedAgentType.value)
}

/** 切换模型偏好 */
function handleModelChange(provider: string): void {
  if (provider === '__config') {
    modelConfigVisible.value = true
    return
  }
  const model = agentStore.models.find((m) => m.provider === provider)
  if (!model || model.status !== 'available') {
    ElMessage.warning('该模型当前不可用或未配置 API Key')
    return
  }
  preferredModel.value = `${model.provider} / ${model.model}`
  // 临时更新当前会话的模型偏好（后端发送消息时会根据可用性自动路由）
  if (agentStore.currentSession) {
    agentStore.currentSession.model_name = model.model
  }
  ElMessage.success(`已切换模型偏好为 ${model.provider} / ${model.model}`)
}

/** 滚动到底部 */
async function scrollToBottom(): Promise<void> {
  await nextTick()
  if (messageContainerRef.value) {
    messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight
  }
}

/** 格式化时间 */
function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

/** 简易Markdown渲染 */
function renderMarkdown(text: string): string {
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>')
}

// 消息变化时自动滚动
watch(
  () => agentStore.messages.length,
  () => scrollToBottom()
)

onMounted(async () => {
  await Promise.all([
    agentStore.fetchAgentTypes(),
    agentStore.fetchScenes(),
    agentStore.fetchModels(),
  ])
  if (!agentStore.agentTypes.some((item) => item.agent_type === selectedAgentType.value)) {
    selectedAgentType.value = agentStore.agentTypes[0]?.agent_type ?? 'general'
  }
  await agentStore.fetchSessions(1, 20, selectedAgentType.value)

  // 如果 URL 中有 sessionId，自动选择该会话
  const sessionId = route.params.sessionId as string
  if (sessionId) {
    await agentStore.selectSession(sessionId)
    await scrollToBottom()
  }
})
</script>

<style lang="scss" scoped>
.agent-chat {
  display: flex;
  height: 100%;
  background: #fff;

  &__sidebar {
    width: 280px;
    border-right: 1px solid #e8e8e8;
    display: flex;
    flex-direction: column;
    background: #fafafa;
  }

  &__sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid #e8e8e8;

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin: 0;
    }
  }

  &__type-selector {
    padding: 12px 16px;
    border-bottom: 1px solid #e8e8e8;
  }

  &__session-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  &__session-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: #f0f0f0;
    }

    &--active {
      background: #e3f2fd;
    }
  }

  &__session-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    overflow: hidden;
  }

  &__session-title {
    font-size: 14px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__session-meta {
    font-size: 12px;
    color: #999;
  }

  &__main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  &__header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    border-bottom: 1px solid #e8e8e8;
    background: #fff;
  }

  &__header-info {
    display: flex;
    flex-direction: column;
  }

  &__header-name {
    font-size: 15px;
    font-weight: 600;
  }

  &__header-desc {
    font-size: 12px;
    color: #999;
  }

  &__model-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
    padding: 4px 12px;
    border-radius: 16px;
    background: #f5f5f5;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: #eaeaea;
    }
  }

  &__model-arrow {
    font-size: 10px;
    color: #999;
  }

  &__model-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &--green {
      background: #4caf50;
    }
    &--yellow {
      background: #ff9800;
    }
    &--red {
      background: #f44336;
    }
  }

  &__model-name {
    font-size: 12px;
    color: #666;
  }

  &__model-option {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 180px;
  }

  &__model-option-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &--green {
      background: #4caf50;
    }

    &--gray {
      background: #bdbdbd;
    }
  }

  &__model-option-name {
    flex: 1;
    font-size: 13px;
  }

  &__model-option-status {
    font-size: 12px;
    color: #999;
  }

  &__model-config-icon {
    font-size: 14px;
    color: #666;
  }

  &__messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  &__message {
    display: flex;
    gap: 10px;
    max-width: 80%;

    &--user {
      align-self: flex-end;
      flex-direction: row-reverse;

      .agent-chat__message-bubble {
        background: #1976d2;
        color: #fff;
      }

      .agent-chat__message-time {
        text-align: right;
      }
    }

    &--assistant {
      align-self: flex-start;
    }
  }

  &__message-content {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  &__message-bubble {
    padding: 10px 14px;
    border-radius: 12px;
    background: #f5f5f5;
    font-size: 14px;
    line-height: 1.6;
    word-break: break-word;

    &--streaming {
      background: #f5f5f5;
    }

    &--loading {
      display: flex;
      gap: 4px;
      padding: 14px 20px;
    }

    :deep(pre) {
      background: #1e1e1e;
      color: #d4d4d4;
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
      margin: 8px 0;
    }

    :deep(code) {
      font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
      font-size: 13px;
    }

    :deep(code:not(pre code)) {
      background: rgba(0, 0, 0, 0.06);
      padding: 2px 6px;
      border-radius: 4px;
    }
  }

  &__message-time {
    font-size: 11px;
    color: #bbb;
  }

  &__cursor {
    animation: blink 1s infinite;
    color: #1976d2;
    font-weight: bold;
  }

  &__dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #999;
    animation: dotPulse 1.4s infinite ease-in-out;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }
    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }

  &__input-area {
    display: flex;
    gap: 10px;
    padding: 16px 20px;
    border-top: 1px solid #e8e8e8;
    background: #fff;
    align-items: flex-end;

    :deep(.el-textarea__inner) {
      border-radius: 8px;
    }
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

@keyframes dotPulse {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

@media (max-width: 768px) {
  .agent-chat {
    &__sidebar {
      width: 100%;
      position: absolute;
      z-index: 10;
      height: 100%;
    }
    &__message {
      max-width: 95%;
    }
  }
}
</style>
