<template>
  <div class="help-center">
    <div class="help-center__header">
      <h1>帮助中心</h1>
      <el-input
        v-model="searchQuery"
        placeholder="搜索帮助内容..."
        prefix-icon="Search"
        clearable
        style="width: 360px; max-width: 100%"
        size="large"
      />
    </div>

    <!-- 使用指南分类 -->
    <el-row :gutter="16" class="help-center__categories">
      <el-col :xs="12" :sm="8" :md="6" v-for="cat in categories" :key="cat.title">
        <div class="help-center__category-card" @click="selectedCategory = cat.key">
          <el-icon :size="32" :color="cat.color"><component :is="cat.icon" /></el-icon>
          <h4>{{ cat.title }}</h4>
          <p>{{ cat.description }}</p>
        </div>
      </el-col>
    </el-row>

    <!-- FAQ折叠面板 -->
    <el-card shadow="never" class="help-center__faq-card">
      <template #header>
        <h3>常见问题</h3>
      </template>
      <el-collapse v-model="activeNames" accordion>
        <el-collapse-item
          v-for="faq in filteredFaqs"
          :key="faq.id"
          :title="faq.question"
          :name="faq.id"
        >
          <div class="help-center__faq-answer" v-html="faq.answer"></div>
        </el-collapse-item>
      </el-collapse>
      <el-empty v-if="filteredFaqs.length === 0" description="没有找到相关问题" :image-size="60" />
    </el-card>

    <!-- 联系支持 -->
    <el-card shadow="never" class="help-center__contact-card">
      <template #header>
        <h3>联系支持</h3>
      </template>
      <el-row :gutter="16">
        <el-col :xs="24" :sm="8">
          <div class="help-center__contact-item">
            <el-icon :size="28" color="#1976D2"><ChatDotRound /></el-icon>
            <h5>在线客服</h5>
            <p>工作日 9:00-18:00</p>
            <el-button type="primary" size="small" @click="openChat">开始对话</el-button>
          </div>
        </el-col>
        <el-col :xs="24" :sm="8">
          <div class="help-center__contact-item">
            <el-icon :size="28" color="#388E3C"><Message /></el-icon>
            <h5>邮件支持</h5>
            <p>support@ai4edu.com</p>
            <el-button type="success" size="small" @click="sendEmail">发送邮件</el-button>
          </div>
        </el-col>
        <el-col :xs="24" :sm="8">
          <div class="help-center__contact-item">
            <el-icon :size="28" color="#F57C00"><Phone /></el-icon>
            <h5>电话支持</h5>
            <p>400-888-9999</p>
            <el-button type="warning" size="small" @click="callSupport">拨打电话</el-button>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 帮助中心
 * FAQ折叠面板 + 使用指南分类 + 联系支持入口
 */
import { ref, computed } from 'vue'
import { ChatDotRound, Message, Phone } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchQuery = ref<string>('')
const selectedCategory = ref<string>('')
const activeNames = ref<string>('')

// 使用指南分类
const categories = ref([
  { key: 'getting-started', title: '快速入门', description: '了解平台基本功能', icon: 'Compass', color: '#1976D2' },
  { key: 'knowledge-graph', title: '知识图谱', description: '构建你的知识网络', icon: 'Connection', color: '#388E3C' },
  { key: 'ai-assistant', title: 'AI助手', description: '与AI智能体互动', icon: 'ChatDotRound', color: '#7B1FA2' },
  { key: 'notes', title: '笔记管理', description: '记录与AI增强', icon: 'EditPen', color: '#F57C00' },
  { key: 'diagnosis', title: '学习诊断', description: '了解学习状况', icon: 'DataAnalysis', color: '#D32F2F' },
  { key: 'classroom', title: '课堂互动', description: '参与课堂活动', icon: 'School', color: '#0288D1' },
])

// FAQ数据
const faqs = ref([
  { id: '1', category: 'getting-started', question: '如何开始使用智慧学伴？', answer: '注册账号后，系统会引导你完成角色选择和兴趣设置。根据你的角色（学生/教师），平台会自动推荐最适合的学习场景和功能。' },
  { id: '2', category: 'getting-started', question: '场景模式有什么区别？', answer: '智慧学伴提供四种场景模式：<br/><strong>课堂模式</strong>：适合跟随课堂节奏学习<br/><strong>自习模式</strong>：适合自主学习和知识探索<br/><strong>考前模式</strong>：适合考试复习和错题练习<br/><strong>讨论模式</strong>：适合小组协作和知识分享' },
  { id: '3', category: 'knowledge-graph', question: '知识图谱怎么用？', answer: '知识图谱展示了知识点之间的关联关系。你可以点击节点查看知识点详情，通过连线了解前置知识和后续知识。AI会根据你的学习状态推荐最需要关注的节点。' },
  { id: '4', category: 'ai-assistant', question: 'AI助手能做什么？', answer: 'AI助手可以：回答学习问题、讲解知识点、生成练习题、批改作业、制定学习计划等。不同类型的AI助手有不同的专长领域。' },
  { id: '5', category: 'notes', question: 'AI增强笔记是什么？', answer: 'AI增强功能可以帮你：自动生成笔记摘要、提取关键知识点、扩展笔记内容、纠正错误，以及关联知识图谱中的相关节点。' },
  { id: '6', category: 'notes', question: '笔记版本历史如何使用？', answer: '每次保存笔记都会生成一个版本。你可以查看历史版本、对比差异、回退到之前的版本。系统还会自动标记AI增强导致的版本变化。' },
  { id: '7', category: 'diagnosis', question: '学习诊断准确吗？', answer: '学习诊断基于你作答的正确率和响应时间综合评估。诊断题目由AI根据你的学习进度动态生成，覆盖不同难度层级，确保评估结果的准确性。' },
  { id: '8', category: 'classroom', question: '课堂互动如何参与？', answer: '加入课堂后，你可以参与实时投票、举手提问、发送弹幕等互动。教师可以发起随堂测验，系统会实时统计全班答题情况。' },
  { id: '9', category: 'getting-started', question: '数据安全如何保障？', answer: '智慧学伴严格遵守数据安全规范，所有个人数据加密存储，AI训练数据经过脱敏处理。你可以随时在设置中管理数据授权和隐私选项。' },
  { id: '10', category: 'ai-assistant', question: '学伴和AI助手有什么区别？', answer: 'AI助手侧重知识解答和学习辅导，功能更专业；学伴更注重情感陪伴和学习动力，风格更温馨。你可以根据需要选择使用。' },
])

/** 搜索过滤FAQ */
const filteredFaqs = computed(() => {
  let result = faqs.value

  if (selectedCategory.value) {
    result = result.filter((f) => f.category === selectedCategory.value)
  }

  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (f) => f.question.toLowerCase().includes(query) || f.answer.toLowerCase().includes(query)
    )
  }

  return result
})

function openChat(): void {
  router.push({ name: 'SceneAIChat' })
}

function sendEmail(): void {
  window.open('mailto:support@ai4edu.com')
}

function callSupport(): void {
  window.open('tel:4008889999')
}
</script>

<style lang="scss" scoped>
.help-center {
  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 12px;

    h1 {
      font-size: 24px;
      font-weight: 700;
      color: #303133;
      margin: 0;
    }
  }

  &__categories {
    margin-bottom: 24px;
  }

  &__category-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 20px 12px;
    background: #fff;
    border-radius: 12px;
    border: 2px solid transparent;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;
    margin-bottom: 12px;

    &:hover {
      border-color: #1976D2;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    h4 {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }

    p {
      font-size: 12px;
      color: #909399;
      margin: 0;
    }
  }

  &__faq-card {
    margin-bottom: 24px;

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin: 0;
    }
  }

  &__faq-answer {
    font-size: 14px;
    line-height: 1.8;
    color: #606266;
    padding: 4px 0;

    :deep(strong) {
      color: #303133;
    }
  }

  &__contact-card {
    h3 {
      font-size: 16px;
      font-weight: 600;
      margin: 0;
    }
  }

  &__contact-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 20px 12px;
    background: #fafafa;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 12px;

    h5 {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }

    p {
      font-size: 13px;
      color: #909399;
      margin: 0;
    }
  }
}
</style>
