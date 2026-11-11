<template>
  <div class="buddy-chat">
    <!-- 温馨头部 -->
    <div class="buddy-chat__header">
      <div class="buddy-chat__avatar-wrap">
        <el-avatar :size="48" :style="{ backgroundColor: '#388E3C' }">
          <el-icon :size="26"><Sunny /></el-icon>
        </el-avatar>
        <span class="buddy-chat__status-dot"></span>
      </div>
      <div class="buddy-chat__header-info">
        <h3>{{ buddyName }}</h3>
        <span class="buddy-chat__header-status">在线 · 随时为你加油</span>
      </div>
      <div class="buddy-chat__mood">
        <span class="buddy-chat__mood-label">今日心情</span>
        <div class="buddy-chat__mood-options">
          <span
            v-for="mood in moods"
            :key="mood.emoji"
            :class="['buddy-chat__mood-item', { 'buddy-chat__mood-item--active': selectedMood === mood.emoji }]"
            @click="selectMood(mood.emoji)"
          >
            {{ mood.emoji }}
          </span>
        </div>
      </div>
    </div>

    <!-- 消息区域 -->
    <div ref="messageContainerRef" class="buddy-chat__messages">
      <div
        v-for="msg in messages"
        :key="msg.id"
        :class="['buddy-chat__message', `buddy-chat__message--${msg.role}`]"
      >
        <!-- 学伴消息 -->
        <template v-if="msg.role === 'buddy'">
          <el-avatar :size="32" :style="{ backgroundColor: '#388E3C' }">
            <el-icon :size="16"><Sunny /></el-icon>
          </el-avatar>
          <div class="buddy-chat__bubble buddy-chat__bubble--buddy">
            {{ msg.content }}
          </div>
        </template>

        <!-- 用户消息 -->
        <template v-else-if="msg.role === 'user'">
          <div class="buddy-chat__bubble buddy-chat__bubble--user">
            {{ msg.content }}
          </div>
        </template>

        <!-- 鼓励消息 -->
        <template v-else-if="msg.role === 'encourage'">
          <div class="buddy-chat__encourage">
            <span class="buddy-chat__encourage-icon">🌟</span>
            <span class="buddy-chat__encourage-text">{{ msg.content }}</span>
          </div>
        </template>

        <!-- 学习计划卡片 -->
        <template v-else-if="msg.role === 'plan'">
          <div class="buddy-chat__plan-card">
            <h4>📋 {{ msg.title }}</h4>
            <ul class="buddy-chat__plan-list">
              <li v-for="(item, idx) in msg.items" :key="idx">
                <el-checkbox v-model="item.done" />
                <span :class="{ 'buddy-chat__plan-done': item.done }">{{ item.text }}</span>
              </li>
            </ul>
          </div>
        </template>
      </div>

      <!-- 快捷回复 -->
      <div class="buddy-chat__quick-replies">
        <el-button
          v-for="reply in quickReplies"
          :key="reply"
          size="small"
          round
          @click="sendQuickReply(reply)"
        >
          {{ reply }}
        </el-button>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="buddy-chat__input-area">
      <el-input
        v-model="inputMessage"
        placeholder="跟学伴聊聊..."
        size="large"
        @keyup.enter="sendMessage"
      >
        <template #prefix>
          <el-icon color="#388E3C"><Sunny /></el-icon>
        </template>
      </el-input>
      <el-button type="success" :icon="Promotion" @click="sendMessage" :disabled="!inputMessage.trim()">
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 学伴聊天页
 * 温馨对话界面 + 学习计划卡片 + 心情记录 + 鼓励消息
 */
import { ref, reactive, nextTick, onMounted } from 'vue'
import { Promotion, Sunny } from '@element-plus/icons-vue'
import { getBuddyProfile, chatWithBuddy, getBuddyMood } from '@/services/buddy'
import { ElMessage } from 'element-plus'

const inputMessage = ref<string>('')
const selectedMood = ref<string>('😊')
const messageContainerRef = ref<HTMLElement | null>(null)
const buddyName = ref<string>('学伴小绿')
const buddyLoading = ref<boolean>(false)

interface PlanItem {
  text: string
  done: boolean
}

interface BuddyMessage {
  id: string
  role: 'user' | 'buddy' | 'encourage' | 'plan'
  content: string
  title?: string
  items?: PlanItem[]
}

const moods = [
  { emoji: '😊', label: '开心' },
  { emoji: '😐', label: '一般' },
  { emoji: '😢', label: '难过' },
  { emoji: '😤', label: '烦躁' },
  { emoji: '😴', label: '疲惫' },
]

const quickReplies = ref([
  '帮我制定学习计划',
  '今天学了什么',
  '给我一些鼓励',
  '推荐学习方法',
])

const messages = reactive<BuddyMessage[]>([
  {
    id: '1',
    role: 'buddy',
    content: '嗨！我是你的学伴小绿 🌱 今天学习怎么样？有什么我可以帮你的吗？',
  },
  {
    id: '2',
    role: 'encourage',
    content: '每一天的努力都是通向成功的阶梯，加油！',
  },
])

async function sendMessage(): Promise<void> {
  const content = inputMessage.value.trim()
  if (!content || buddyLoading.value) return

  // 添加用户消息
  messages.push({
    id: `msg_${Date.now()}`,
    role: 'user',
    content,
  })
  inputMessage.value = ''

  await nextTick()
  scrollToBottom()

  // 调用后端 API
  buddyLoading.value = true
  try {
    const result = await chatWithBuddy(content)
    messages.push({
      id: `buddy_${Date.now()}`,
      role: 'buddy',
      content: result.content || '学伴正在思考...',
    })
  } catch (e: any) {
    ElMessage.error(e.message || '学伴暂时不在，请稍后再试')
    messages.push({
      id: `buddy_${Date.now()}`,
      role: 'buddy',
      content: '抱歉，我刚才走神了，能再说一遍吗？',
    })
  } finally {
    buddyLoading.value = false
    nextTick(() => scrollToBottom())
  }
}

function sendQuickReply(reply: string): void {
  inputMessage.value = reply
  sendMessage()
}

/** 根据心情生成回复（前端模拟，可接入 GET /mood） */
async function selectMood(emoji: string): Promise<void> {
  selectedMood.value = emoji
  try {
    // 记录心情；回复文案由前端按心情生成，后端返回的 BuddyMoodResult 不含 message 字段
    await getBuddyMood()
    messages.push({
      id: `mood_${Date.now()}`,
      role: 'buddy',
      content: getMoodResponse(emoji),
    })
  } catch {
    messages.push({
      id: `mood_${Date.now()}`,
      role: 'buddy',
      content: getMoodResponse(emoji),
    })
  }
  nextTick(() => scrollToBottom())
}

/** 根据心情生成回复 */
function getMoodResponse(emoji: string): string {
  const responses: Record<string, string> = {
    '😊': '看到你心情不错！学习效率也会更高哦，继续保持！',
    '😐': '状态一般也没关系，不如我们先做点轻松的复习，慢慢进入状态？',
    '😢': '别难过，学习路上总有高低。跟我聊聊，也许能感觉好一些 💪',
    '😤': '深呼吸~ 暂时放空一下，然后我们重新开始，好吗？',
    '😴': '累了就休息一下吧！休息好才能学得好。需要我帮你安排一段短休吗？',
  }
  return responses[emoji] || '不管什么心情，学伴都在这里陪着你！'
}

function scrollToBottom(): void {
  if (messageContainerRef.value) {
    messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight
  }
}

onMounted(async () => {
  try {
    const profile = await getBuddyProfile()
    if (profile?.name) {
      buddyName.value = profile.name
    }
  } catch (e) {
    console.warn('获取学伴配置失败，使用默认名称', e)
  }
})
</script>

<style lang="scss" scoped>
.buddy-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: linear-gradient(180deg, #f1f8e9 0%, #ffffff 40%);

  &__header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 20px;
    border-bottom: 1px solid #e8e8e8;
    background: #fff;
  }

  &__avatar-wrap {
    position: relative;
  }

  &__status-dot {
    position: absolute;
    bottom: 2px;
    right: 2px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #4caf50;
    border: 2px solid #fff;
  }

  &__header-info {
    flex: 1;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }

  &__header-status {
    font-size: 12px;
    color: #388E3C;
  }

  &__mood {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
  }

  &__mood-label {
    font-size: 11px;
    color: #909399;
  }

  &__mood-options {
    display: flex;
    gap: 4px;
  }

  &__mood-item {
    font-size: 20px;
    cursor: pointer;
    transition: transform 0.2s;
    padding: 2px;

    &:hover {
      transform: scale(1.3);
    }

    &--active {
      transform: scale(1.3);
      background: #e8f5e9;
      border-radius: 6px;
    }
  }

  &__messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  &__message {
    display: flex;
    gap: 10px;
    max-width: 75%;

    &--user {
      align-self: flex-end;
    }

    &--buddy {
      align-self: flex-start;
    }

    &--encourage, &--plan {
      align-self: center;
      max-width: 90%;
    }
  }

  &__bubble {
    padding: 10px 14px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-line;

    &--buddy {
      background: #e8f5e9;
      color: #2e7d32;
      border-bottom-left-radius: 4px;
    }

    &--user {
      background: #388E3C;
      color: #fff;
      border-bottom-right-radius: 4px;
    }
  }

  &__encourage {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    background: linear-gradient(135deg, #fff9c4, #fff3e0);
    border-radius: 20px;
    border: 1px solid #ffe082;
  }

  &__encourage-icon {
    font-size: 20px;
  }

  &__encourage-text {
    font-size: 14px;
    color: #e65100;
    font-weight: 500;
  }

  &__plan-card {
    background: #fff;
    border-radius: 12px;
    border: 2px solid #c8e6c9;
    padding: 16px;
    width: 100%;

    h4 {
      font-size: 15px;
      font-weight: 600;
      color: #2e7d32;
      margin: 0 0 12px;
    }
  }

  &__plan-list {
    list-style: none;
    padding: 0;
    margin: 0;

    li {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }
    }
  }

  &__plan-done {
    text-decoration: line-through;
    color: #bdbdbd;
  }

  &__quick-replies {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px 20px 0;
  }

  &__input-area {
    display: flex;
    gap: 10px;
    padding: 14px 20px;
    border-top: 1px solid #e8e8e8;
    background: #fff;
    align-items: center;
  }
}

@media (max-width: 768px) {
  .buddy-chat {
    &__message {
      max-width: 90%;
    }
    &__mood {
      display: none;
    }
  }
}
</style>
