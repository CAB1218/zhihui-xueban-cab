<template>
  <div class="lesson-plan">
    <div class="lesson-plan__header">
      <h2>AI 备课助手</h2>
      <p class="lesson-plan__subtitle">输入课程目标，AI帮你生成完整教案</p>
    </div>

    <div class="lesson-plan__saved">
      <div class="lesson-plan__saved-header">
        <h3>已保存教案</h3>
        <span>点击教案图标可在当前页面查看</span>
      </div>
      <div v-if="savedPlans.length" class="lesson-plan__saved-list">
        <button
          v-for="plan in savedPlans"
          :key="plan.id"
          :class="['lesson-plan__saved-card', { 'lesson-plan__saved-card--active': savedPlanId === plan.id }]"
          @click="openSavedPlan(plan.id)"
        >
          <span class="lesson-plan__saved-icon"><el-icon><Document /></el-icon></span>
          <span class="lesson-plan__saved-info">
            <strong>{{ plan.title }}</strong>
            <small>{{ formatSavedTime(plan.updated_at) }}</small>
          </span>
          <el-tag size="small" :type="plan.ai_generated ? 'primary' : 'info'">
            {{ plan.ai_generated ? 'AI 教案' : '教案' }}
          </el-tag>
        </button>
      </div>
      <el-empty v-else description="尚未保存教案" :image-size="54" />
    </div>

    <div class="lesson-plan__body">
      <!-- 左侧：输入+生成 -->
      <div class="lesson-plan__input-panel">
        <el-form :model="planForm" label-position="top">
          <el-form-item label="课程名称">
            <el-input v-model="planForm.courseName" placeholder="如：高等数学" />
          </el-form-item>
          <el-form-item label="教学目标">
            <el-input
              v-model="planForm.objectives"
              type="textarea"
              :rows="3"
              placeholder="描述本次课的教学目标..."
            />
          </el-form-item>
          <el-form-item label="知识点">
            <el-select
              v-model="planForm.knowledgePoints"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="添加知识点"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="教学时长">
            <el-select v-model="planForm.duration" style="width: 100%">
              <el-option label="1课时（45分钟）" value="45" />
              <el-option label="2课时（90分钟）" value="90" />
              <el-option label="3课时（135分钟）" value="135" />
            </el-select>
          </el-form-item>
          <el-form-item label="学生水平">
            <el-radio-group v-model="planForm.studentLevel">
              <el-radio-button value="basic">基础</el-radio-button>
              <el-radio-button value="intermediate">中等</el-radio-button>
              <el-radio-button value="advanced">提高</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="generating" @click="generatePlan" style="width: 100%">
              <el-icon><MagicStick /></el-icon> AI 生成教案
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 右侧：教案预览和编辑 -->
      <div class="lesson-plan__preview-panel">
        <div v-if="!generatedPlan && !generating" class="lesson-plan__empty">
          <el-icon :size="64" color="#dcdfe6"><Document /></el-icon>
          <p>在左侧输入课程信息，AI将为你生成完整教案</p>
        </div>

        <div v-if="generating" class="lesson-plan__generating">
          <el-icon :size="40" class="lesson-plan__spin"><Loading /></el-icon>
          <p>AI正在生成教案...</p>
        </div>

        <div v-if="generatedPlan && !generating" class="lesson-plan__result">
          <div class="lesson-plan__result-header">
            <h3>{{ generatedPlan.title }}</h3>
            <div class="lesson-plan__result-actions">
              <el-button size="small" @click="editPlan">编辑</el-button>
              <el-button size="small" type="primary" :loading="saving" @click="savePlan">保存教案</el-button>
            </div>
          </div>
          <div class="lesson-plan__result-content">
            <section class="lesson-plan__section">
              <h4>教学目标</h4>
              <ul>
                <li v-for="(obj, idx) in generatedPlan.objectives" :key="idx">{{ obj }}</li>
              </ul>
            </section>
            <section class="lesson-plan__section">
              <h4>教学过程</h4>
              <div v-for="(step, idx) in generatedPlan.steps" :key="idx" class="lesson-plan__step">
                <div class="lesson-plan__step-header">
                  <el-tag size="small" type="primary">步骤 {{ idx + 1 }}</el-tag>
                  <span class="lesson-plan__step-title">{{ step.title }}</span>
                  <span class="lesson-plan__step-duration">{{ step.duration }}分钟</span>
                </div>
                <p class="lesson-plan__step-content">{{ step.content }}</p>
              </div>
            </section>
            <section class="lesson-plan__section">
              <h4>课后作业</h4>
              <ul>
                <li v-for="(hw, idx) in generatedPlan.homework" :key="idx">{{ hw }}</li>
              </ul>
            </section>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：相关资源推荐 -->
    <div v-if="generatedPlan" class="lesson-plan__resources">
      <h3>相关资源推荐</h3>
      <el-row :gutter="12">
        <el-col :xs="12" :sm="8" :md="6" v-for="res in recommendedResources" :key="res.title">
          <div class="lesson-plan__resource-card" @click="goToResource(res.id)">
            <el-icon :size="20" color="#1976D2"><Document /></el-icon>
            <div class="lesson-plan__resource-info">
              <span class="lesson-plan__resource-title">{{ res.title }}</span>
              <span class="lesson-plan__resource-type">{{ res.type }}</span>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 备课助手页
 * 左侧输入+AI生成 + 右侧教案预览 + 底部资源推荐
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick, Document, Loading } from '@element-plus/icons-vue'
import api from '@/services/api'

const router = useRouter()
const route = useRoute()
const courseId = ref<number | null>(null)

const generating = ref<boolean>(false)
const saving = ref<boolean>(false)

const planForm = reactive({
  courseName: '',
  objectives: '',
  knowledgePoints: [] as string[],
  duration: '90',
  studentLevel: 'intermediate',
})

interface PlanStep {
  title: string
  duration: number
  content: string
}

interface GeneratedPlan {
  title: string
  objectives: string[]
  steps: PlanStep[]
  homework: string[]
}

interface SavedPlan {
  id: number
  title: string
  course_id: number
  duration_minutes: number
  ai_generated: boolean
  updated_at: string
}

interface SavedPlanDetail extends SavedPlan {
  objectives: string[]
  content: string | null
  materials: string[]
}

const generatedPlan = ref<GeneratedPlan | null>(null)
const savedPlans = ref<SavedPlan[]>([])
const savedPlanId = ref<number | null>(null)

const recommendedResources = ref([
  { id: 1, title: '微积分基础教程', type: 'PDF文档' },
  { id: 2, title: '极限与连续讲解', type: '视频' },
  { id: 3, title: '导数练习题集', type: 'PDF文档' },
  { id: 4, title: '微积分思维导图', type: '图片' },
])

async function generatePlan(): Promise<void> {
  if (!planForm.courseName.trim()) {
    ElMessage.warning('请输入课程名称')
    return
  }

  generating.value = true
  savedPlanId.value = null
  try {
    const response = await api.post('/teachers/lesson-plans/generate-preview', {
      course_name: planForm.courseName,
      objectives: planForm.objectives,
      knowledge_points: planForm.knowledgePoints,
      duration: Number(planForm.duration),
      student_level: planForm.studentLevel,
    })
    generatedPlan.value = response.data as GeneratedPlan
    ElMessage.success('教案生成成功')
  } catch (error) {
    console.error('生成教案失败:', error)
    // 降级：使用模拟数据
    generatedPlan.value = {
      title: `${planForm.courseName} — 教案`,
      objectives: [
        '理解核心概念的定义和内涵',
        '掌握基本定理的证明思路',
        '能够运用所学知识解决实际问题',
      ],
      steps: [
        { title: '导入新课', duration: 10, content: '通过生活实例引入，激发学生兴趣，建立新旧知识的联系。' },
        { title: '概念讲解', duration: 25, content: '详细讲解核心概念，配合图示和示例，帮助学生建立直观理解。' },
        { title: '互动练习', duration: 20, content: '设计分层练习题，从基础到进阶，让不同水平的学生都有收获。' },
        { title: '总结提升', duration: 10, content: '回顾本节课重点，引导学生归纳知识框架，布置课后拓展任务。' },
      ],
      homework: [
        '完成课本P45 第1-5题',
        '整理本节课知识框架图',
        '预习下节内容并写出疑问',
      ],
    }
  } finally {
    generating.value = false
  }
}

function editPlan(): void {
  ElMessage.info('教案编辑功能开发中')
}

async function savePlan(): Promise<void> {
  if (!generatedPlan.value) {
    ElMessage.warning('请先生成教案')
    return
  }

  saving.value = true
  try {
    const response = await api.post('/teachers/lesson-plans', {
      course_id: courseId.value ?? undefined,
      course_name: planForm.courseName.trim(),
      title: generatedPlan.value.title,
      objectives: generatedPlan.value.objectives,
      content: JSON.stringify({
        steps: generatedPlan.value.steps,
        homework: generatedPlan.value.homework,
      }),
      materials: generatedPlan.value.homework,
      duration_minutes: Number(planForm.duration),
      ai_generated: true,
    })
    const saved = response.data as { id: number }
    savedPlanId.value = saved.id
    await loadSavedPlans()
    ElMessage.success('教案已保存')
  } catch (error) {
    console.error('保存教案失败:', error)
  } finally {
    saving.value = false
  }
}

function goToResource(id: number): void {
  router.push({ name: 'ResourceDetail', params: { id } })
}

async function loadSavedPlans(): Promise<void> {
  const response = await api.get('/teachers/lesson-plans', {
    params: { page: 1, page_size: 50, course_id: courseId.value ?? undefined },
  })
  const data = response.data as { items: SavedPlan[] }
  savedPlans.value = data.items ?? []
}

async function openSavedPlan(planId: number): Promise<void> {
  try {
    const response = await api.get(`/teachers/lesson-plans/${planId}`)
    const plan = response.data as SavedPlanDetail
    let steps: PlanStep[] = []
    let homework: string[] = plan.materials ?? []

    if (plan.content) {
      try {
        const content = JSON.parse(plan.content) as { steps?: PlanStep[]; homework?: string[] }
        steps = content.steps ?? []
        homework = content.homework ?? homework
      } catch {
        steps = [{ title: '教学内容', duration: plan.duration_minutes, content: plan.content }]
      }
    }

    generatedPlan.value = {
      title: plan.title,
      objectives: plan.objectives ?? [],
      steps,
      homework,
    }
    courseId.value = plan.course_id
    planForm.duration = String(plan.duration_minutes)
    savedPlanId.value = plan.id
    ElMessage.success('已打开保存的教案')
  } catch (error) {
    console.error('打开教案失败:', error)
  }
}

function formatSavedTime(value: string): string {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(async () => {
  const routeCourseId = Number(route.params.id)
  if (route.name === 'TeacherCourseDetail' && Number.isFinite(routeCourseId)) {
    courseId.value = routeCourseId
    planForm.courseName = String(route.query.name ?? '')
  }
  await loadSavedPlans()
  if (route.name === 'TeacherLessonPlanDetail' && Number.isFinite(routeCourseId)) {
    await openSavedPlan(routeCourseId)
  }
})
</script>

<style lang="scss" scoped>
.lesson-plan {
  &__saved {
    padding: 16px 20px;
    margin-bottom: 20px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  }

  &__saved-header {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 14px;

    h3 { margin: 0; font-size: 16px; }
    span { font-size: 12px; color: #909399; }
  }

  &__saved-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 12px;
  }

  &__saved-card {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    padding: 12px;
    font: inherit;
    text-align: left;
    cursor: pointer;
    background: #fafafa;
    border: 1px solid #ebeef5;
    border-radius: 10px;
    transition: all 0.2s;

    &:hover, &--active { border-color: #409eff; background: #ecf5ff; }
  }

  &__saved-icon {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    flex-shrink: 0;
    color: #1976d2;
    font-size: 22px;
    background: #e3f2fd;
    border-radius: 10px;
  }

  &__saved-info {
    display: flex;
    flex: 1;
    min-width: 0;
    flex-direction: column;
    gap: 4px;

    strong { overflow: hidden; font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
    small { color: #909399; }
  }

  &__header {
    margin-bottom: 20px;

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

  &__body {
    display: flex;
    gap: 20px;
    min-height: 500px;
  }

  &__input-panel {
    width: 360px;
    flex-shrink: 0;
    background: #fff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    overflow-y: auto;
  }

  &__preview-panel {
    flex: 1;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    overflow-y: auto;
  }

  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: #c0c4cc;
    padding: 40px;

    p {
      font-size: 14px;
    }
  }

  &__generating {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 16px;
    color: #909399;
  }

  &__spin {
    animation: spin 1s linear infinite;
  }

  &__result {
    padding: 24px;
  }

  &__result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid #1976D2;

    h3 {
      font-size: 20px;
      font-weight: 700;
      color: #303133;
      margin: 0;
    }
  }

  &__result-actions {
    display: flex;
    gap: 8px;
  }

  &__result-content {
    line-height: 1.8;
  }

  &__section {
    margin-bottom: 24px;

    h4 {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 12px;
      padding-left: 10px;
      border-left: 3px solid #1976D2;
    }

    ul {
      padding-left: 20px;
      margin: 0;

      li {
        margin-bottom: 6px;
        font-size: 14px;
        color: #606266;
      }
    }
  }

  &__step {
    margin-bottom: 16px;
    padding: 12px 16px;
    background: #fafafa;
    border-radius: 8px;
    border-left: 3px solid #1976D2;
  }

  &__step-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }

  &__step-title {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
  }

  &__step-duration {
    font-size: 12px;
    color: #909399;
    margin-left: auto;
  }

  &__step-content {
    font-size: 14px;
    color: #606266;
    line-height: 1.6;
    margin: 0;
  }

  &__resources {
    margin-top: 24px;
    padding: 20px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin: 0 0 16px;
    }
  }

  &__resource-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: #fafafa;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;
    margin-bottom: 8px;

    &:hover {
      background: #f0f0f0;
    }
  }

  &__resource-info {
    display: flex;
    flex-direction: column;
  }

  &__resource-title {
    font-size: 14px;
    font-weight: 500;
    color: #303133;
  }

  &__resource-type {
    font-size: 12px;
    color: #909399;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .lesson-plan {
    &__body {
      flex-direction: column;
    }
    &__input-panel {
      width: 100%;
    }
  }
}
</style>
