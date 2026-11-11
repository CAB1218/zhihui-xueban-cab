<template>
  <div class="diagnosis-view">
    <div class="diagnosis-view__header">
      <h2>学习诊断</h2>
      <p class="diagnosis-view__subtitle">了解你的学习状况，获取针对性提升建议</p>
    </div>

    <!-- 诊断未开始：选择诊断类型 -->
    <div v-if="phase === 'select'" class="diagnosis-view__select">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="8" v-for="type in diagnosisTypes" :key="type.value">
          <div
            :class="['diagnosis-view__type-card', { 'diagnosis-view__type-card--active': selectedType === type.value }]"
            @click="selectedType = type.value"
          >
            <el-icon :size="36" :color="type.color"><component :is="type.icon" /></el-icon>
            <h4>{{ type.label }}</h4>
            <p>{{ type.description }}</p>
          </div>
        </el-col>
      </el-row>
      <div class="diagnosis-view__start-action">
        <el-button
          type="primary"
          size="large"
          :disabled="!selectedType"
          @click="startDiagnosis"
        >
          开始诊断
        </el-button>
      </div>
    </div>

    <!-- 答题界面 -->
    <div v-else-if="phase === 'quiz'" class="diagnosis-view__quiz">
      <div class="diagnosis-view__quiz-header">
        <el-steps :active="currentQuestionIndex" :total="questions.length" simple />
        <span class="diagnosis-view__quiz-progress">
          {{ currentQuestionIndex + 1 }} / {{ questions.length }}
        </span>
      </div>

      <div class="diagnosis-view__quiz-content">
        <h3 class="diagnosis-view__question-text">
          {{ currentQuestion.question }}
        </h3>

        <!-- 选择题 -->
        <div v-if="currentQuestion.type === 'choice'" class="diagnosis-view__options">
          <div
            v-for="(option, idx) in currentQuestion.options"
            :key="idx"
            :class="[
              'diagnosis-view__option',
              { 'diagnosis-view__option--selected': selectedAnswer === idx },
            ]"
            @click="selectedAnswer = idx"
          >
            <span class="diagnosis-view__option-letter">{{ String.fromCharCode(65 + idx) }}</span>
            <span class="diagnosis-view__option-text">{{ option }}</span>
          </div>
        </div>

        <!-- 填空题 -->
        <div v-else-if="currentQuestion.type === 'fill'" class="diagnosis-view__fill">
          <el-input
            v-model="fillAnswer"
            placeholder="输入你的答案"
            size="large"
            @keyup.enter="submitAnswer"
          />
        </div>
      </div>

      <div class="diagnosis-view__quiz-actions">
        <el-button @click="prevQuestion" :disabled="currentQuestionIndex === 0">上一题</el-button>
        <el-button type="primary" @click="submitAnswer">
          {{ currentQuestionIndex === questions.length - 1 ? '提交诊断' : '下一题' }}
        </el-button>
      </div>
    </div>

    <!-- 诊断报告 -->
    <div v-else-if="phase === 'report'" class="diagnosis-view__report">
      <el-row :gutter="16">
        <!-- 雷达图 -->
        <el-col :xs="24" :lg="12">
          <el-card shadow="never">
            <template #header>
              <h3>能力雷达图</h3>
            </template>
            <div ref="radarChartRef" class="diagnosis-view__radar-chart"></div>
          </el-card>
        </el-col>

        <!-- 知识点得分 -->
        <el-col :xs="24" :lg="12">
          <el-card shadow="never">
            <template #header>
              <h3>知识点得分</h3>
            </template>
            <div class="diagnosis-view__score-list">
              <div
                v-for="point in scoreData"
                :key="point.name"
                class="diagnosis-view__score-item"
              >
                <span class="diagnosis-view__score-name">{{ point.name }}</span>
                <el-progress
                  :percentage="point.score"
                  :stroke-width="10"
                  :color="point.score >= 70 ? '#67c23a' : point.score >= 40 ? '#e6a23c' : '#f56c6c'"
                />
                <span class="diagnosis-view__score-value">{{ point.score }}分</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 学习建议 -->
      <el-card shadow="never" style="margin-top: 16px">
        <template #header>
          <h3>个性化学习建议</h3>
        </template>
        <div class="diagnosis-view__advice-list">
          <el-alert
            v-for="(advice, idx) in advices"
            :key="idx"
            :title="advice.title"
            :description="advice.description"
            :type="advice.type"
            show-icon
            :closable="false"
            class="diagnosis-view__advice"
          />
        </div>
      </el-card>

      <div class="diagnosis-view__report-actions">
        <el-button @click="resetDiagnosis">重新诊断</el-button>
        <el-button type="primary" @click="startLearning">开始学习</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 学习诊断页
 * 诊断类型选择 + 答题界面 + 诊断报告（雷达图+得分+建议）
 */
import { ref, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

type DiagnosisPhase = 'select' | 'quiz' | 'report'

const phase = ref<DiagnosisPhase>('select')
const selectedType = ref<string>('')
const currentQuestionIndex = ref<number>(0)
const selectedAnswer = ref<number | null>(null)
const fillAnswer = ref<string>('')
const radarChartRef = ref<HTMLElement | null>(null)

// 诊断类型
const diagnosisTypes = ref([
  { value: 'knowledge', label: '知识点诊断', description: '检测你对特定知识点的掌握程度', icon: 'Reading', color: '#1976D2' },
  { value: 'comprehensive', label: '综合诊断', description: '全面评估你的学习水平和能力', icon: 'DataAnalysis', color: '#388E3C' },
  { value: 'unit', label: '单元测试', description: '针对某一单元进行深度测评', icon: 'EditPen', color: '#F57C00' },
])

// 模拟题目
const questions = ref([
  { question: '函数f(x)在x₀处连续的充分必要条件是什么？', type: 'choice', options: ['极限存在', '极限等于函数值', '左右极限存在且相等', '可导'], answer: 1, knowledge: '连续' },
  { question: '求lim(x→0) sin(x)/x 的值？', type: 'choice', options: ['0', '1', '∞', '不存在'], answer: 1, knowledge: '极限' },
  { question: '导数的几何意义是？', type: 'fill', answer: '切线斜率', knowledge: '导数' },
  { question: '下列哪个是牛顿-莱布尼茨公式的正确表达？', type: 'choice', options: ['∫[a,b]f(x)dx = F(b) - F(a)', '∫[a,b]f(x)dx = F(a) - F(b)', '∫f(x)dx = F(x)+C', 'F\'(x) = f(x)'], answer: 0, knowledge: '积分' },
  { question: '级数∑(1/n²)是否收敛？', type: 'choice', options: ['发散', '条件收敛', '绝对收敛', '无法判断'], answer: 2, knowledge: '级数' },
])

// 得分数据
const scoreData = ref([
  { name: '极限', score: 85 },
  { name: '连续', score: 72 },
  { name: '导数', score: 60 },
  { name: '积分', score: 45 },
  { name: '级数', score: 55 },
])

// 建议
const advices = ref([
  { title: '加强积分基础', description: '积分知识点得分较低，建议从基本积分公式开始复习，逐步掌握换元积分和分部积分法。', type: 'warning' as const },
  { title: '巩固级数理论', description: '级数部分需要加强判别法的理解，建议多做正项级数判敛的练习题。', type: 'info' as const },
  { title: '导数应用良好', description: '导数部分掌握较好，可以尝试更复杂的导数应用问题，如最值问题和相关变化率。', type: 'success' as const },
])

const currentQuestion = computed(() => questions.value[currentQuestionIndex.value])

function startDiagnosis(): void {
  if (!selectedType.value) {
    ElMessage.warning('请选择诊断类型')
    return
  }
  phase.value = 'quiz'
  currentQuestionIndex.value = 0
  selectedAnswer.value = null
  fillAnswer.value = ''
}

function prevQuestion(): void {
  if (currentQuestionIndex.value > 0) {
    currentQuestionIndex.value--
    selectedAnswer.value = null
    fillAnswer.value = ''
  }
}

function submitAnswer(): void {
  // 保存答案
  if (currentQuestionIndex.value < questions.value.length - 1) {
    currentQuestionIndex.value++
    selectedAnswer.value = null
    fillAnswer.value = ''
  } else {
    // 提交诊断，生成报告
    phase.value = 'report'
    nextTick(() => {
      renderRadarChart()
    })
  }
}

function resetDiagnosis(): void {
  phase.value = 'select'
  selectedType.value = ''
  currentQuestionIndex.value = 0
  selectedAnswer.value = null
  fillAnswer.value = ''
}

function startLearning(): void {
  router.push({ name: 'SceneAIChat' })
}

/** 渲染雷达图（使用ECharts） */
async function renderRadarChart(): Promise<void> {
  if (!radarChartRef.value) return

  try {
    const echarts = await import('echarts')
    const chart = echarts.init(radarChartRef.value)

    const indicators = scoreData.value.map((d) => ({
      name: d.name,
      max: 100,
    }))

    chart.setOption({
      radar: {
        indicator: indicators,
        shape: 'polygon',
        splitNumber: 5,
        axisName: {
          color: '#606266',
          fontSize: 13,
        },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: scoreData.value.map((d) => d.score),
              name: '诊断得分',
              areaStyle: {
                color: 'rgba(25, 118, 210, 0.2)',
              },
              lineStyle: {
                color: '#1976D2',
                width: 2,
              },
              itemStyle: {
                color: '#1976D2',
              },
            },
          ],
        },
      ],
    })

    window.addEventListener('resize', () => chart.resize())
  } catch (error) {
    console.error('ECharts加载失败:', error)
  }
}
</script>

<style lang="scss" scoped>
.diagnosis-view {
  &__header {
    margin-bottom: 24px;

    h2 {
      font-size: 22px;
      font-weight: 700;
      color: #303133;
      margin: 0 0 4px;
    }
  }

  &__subtitle {
    font-size: 14px;
    color: #909399;
    margin: 0;
  }

  &__select {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
  }

  &__type-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 28px 20px;
    background: #fff;
    border: 2px solid #e8e8e8;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: center;

    h4 {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }

    p {
      font-size: 13px;
      color: #909399;
      margin: 0;
    }

    &:hover {
      border-color: #1976D2;
      box-shadow: 0 4px 12px rgba(25, 118, 210, 0.15);
    }

    &--active {
      border-color: #1976D2;
      background: #e3f2fd;
    }
  }

  &__start-action {
    margin-top: 8px;
  }

  &__quiz {
    max-width: 700px;
    margin: 0 auto;
  }

  &__quiz-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  &__quiz-progress {
    font-size: 14px;
    color: #909399;
    white-space: nowrap;
    margin-left: 12px;
  }

  &__quiz-content {
    margin-bottom: 24px;
  }

  &__question-text {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
    line-height: 1.6;
    margin: 0 0 20px;
  }

  &__options {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  &__option {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    border: 2px solid #e8e8e8;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      border-color: #1976D2;
      background: #f5f9ff;
    }

    &--selected {
      border-color: #1976D2;
      background: #e3f2fd;
    }
  }

  &__option-letter {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #f0f0f0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 600;
    color: #606266;
    flex-shrink: 0;
  }

  &__option--selected &__option-letter {
    background: #1976D2;
    color: #fff;
  }

  &__option-text {
    font-size: 15px;
    color: #303133;
  }

  &__fill {
    margin-top: 8px;
  }

  &__quiz-actions {
    display: flex;
    justify-content: space-between;
  }

  &__radar-chart {
    width: 100%;
    height: 350px;
  }

  &__score-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  &__score-item {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  &__score-name {
    font-size: 14px;
    color: #606266;
    min-width: 60px;
  }

  &__score-item :deep(.el-progress) {
    flex: 1;
  }

  &__score-value {
    font-size: 14px;
    font-weight: 600;
    min-width: 40px;
    text-align: right;
  }

  &__advice-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  &__advice {
    margin: 0;
  }

  &__report-actions {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-top: 24px;
  }
}
</style>
