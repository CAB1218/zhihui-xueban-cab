<template>
  <div class="advice-view">
    <!-- ============ 页头 ============ -->
    <div class="page-header">
      <div class="page-header__left">
        <h2>个性化学习建议</h2>
        <span class="page-header__hint">结合学习要求、学情结论与可用材料，给出「学什么 / 怎么练 / 为什么这么排」</span>
      </div>
      <div class="page-header__actions">
        <el-dropdown trigger="click" @command="onImportCommand">
          <el-button :icon="Upload">
            导入<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="students">导入学生名单（建号）</el-dropdown-item>
              <el-dropdown-item command="records">导入学情记录（成绩/答题）</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="primary" :icon="MagicStick" :loading="generating" @click="onGenerate">
          生成建议
        </el-button>
      </div>
    </div>

    <!-- ============ 条件选择 ============ -->
    <el-card shadow="never" class="control-card">
      <el-form :inline="true" class="control-form" @submit.prevent>
        <el-form-item label="课程">
          <el-select v-model="courseId" style="width: 190px" @change="onCourseChange">
            <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生">
          <el-select
            v-model="studentId"
            filterable
            placeholder="选择学生"
            style="width: 240px"
            :loading="loadingStudents"
          >
            <el-option v-for="s in students" :key="s.student_id" :label="s.name" :value="s.student_id">
              <span class="stu-option__name">{{ s.name }}</span>
              <span class="stu-option__meta">
                {{ s.record_count ? `${s.record_count} 条记录` : '暂无记录' }}
                <template v-if="s.accuracy !== null"> · {{ (s.accuracy * 100).toFixed(0) }}%</template>
              </span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="周期">
          <el-select v-model="durationDays" style="width: 110px">
            <el-option :value="3" label="3 天" />
            <el-option :value="7" label="7 天" />
            <el-option :value="14" label="14 天" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先补强">
          <el-input
            v-model="focus"
            placeholder="选填，如「排序」"
            clearable
            style="width: 160px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="generating" @click="onGenerate">生成</el-button>
        </el-form-item>
      </el-form>
      <div class="control-tip">
        依据：任务2 学情结论（个体摘要）＋ 任务1 课程大纲（学习要求与教材出处）＋ 资源库材料。
        <span v-if="outlineHint" class="control-tip__warn">{{ outlineHint }}</span>
      </div>
    </el-card>

    <!-- ============ 空态 ============ -->
    <el-card v-if="!plan" shadow="never" class="empty-card">
      <el-empty description="选择学生后点「生成建议」，会得到一份可直接执行的学习建议">
        <template #description>
          <div class="empty-desc">
            <p>选择「学生 + 课程 + 周期」后点「生成建议」。</p>
            <p class="muted">建议会逐条给出：学什么、对应材料/练习、为什么补它、先做什么后做什么、怎么验收。</p>
            <p class="muted">没有学情数据也能生成——会转为「补充观察」型方案，不预设学生「没学会」。</p>
          </div>
        </template>
      </el-empty>
    </el-card>

    <!-- ============ 结果 ============ -->
    <template v-else>
      <el-card shadow="never" class="summary-card">
        <div class="summary-head">
          <div>
            <span class="summary-head__title">{{ plan.student.name }} · {{ plan.course.name }}</span>
            <el-tag size="small" type="info" class="summary-head__tag">周期 {{ plan.duration_days }} 天</el-tag>
            <el-tag size="small" :type="plan.outline.available ? 'success' : 'warning'" class="summary-head__tag">
              {{ plan.outline.available ? `依据大纲：${plan.outline.title || plan.course.name}` : '未找到大纲，按通用层次生成' }}
            </el-tag>
            <el-tag v-if="plan.focus" size="small" type="warning" class="summary-head__tag">优先：{{ plan.focus }}</el-tag>
          </div>
          <div class="summary-head__actions">
            <el-button size="small" :icon="Download" @click="onExport">导出 MD</el-button>
          </div>
        </div>

        <div class="stat-row">
          <div class="stat">
            <div class="stat__value">{{ plan.summary.attempts }}</div>
            <div class="stat__label">可判断作答</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ plan.summary.accuracy === null ? '—' : `${(plan.summary.accuracy * 100).toFixed(1)}%` }}</div>
            <div class="stat__label">整体正确率</div>
          </div>
          <div class="stat">
            <div class="stat__value stat__value--warn">{{ plan.summary.weak_count }}</div>
            <div class="stat__label">需巩固</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ plan.summary.fair_count }}</div>
            <div class="stat__label">基本掌握</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ plan.summary.insufficient_count }}</div>
            <div class="stat__label">证据不足</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ plan.items.length }}</div>
            <div class="stat__label">补强步骤</div>
          </div>
        </div>

        <div class="goal-box">
          <span class="goal-box__label">本次目标</span>
          <span class="goal-box__text">{{ plan.goal_overview }}</span>
        </div>
      </el-card>

      <!-- 步骤 -->
      <el-card v-for="item in plan.items" :key="item.order" shadow="never" class="step-card">
        <template #header>
          <div class="step-head">
            <span class="step-head__no">第 {{ item.order }} 步</span>
            <span class="step-head__kp">{{ item.knowledge_point }}</span>
            <el-tag size="small" type="warning">{{ item.status_label }}</el-tag>
            <span class="step-head__acc">正确率 {{ item.accuracy === null ? '—' : `${(item.accuracy * 100).toFixed(1)}%` }}</span>
            <span class="step-head__min">约 {{ item.estimated_minutes }} 分钟</span>
          </div>
        </template>

        <div class="step-grid">
          <div class="field">
            <span class="field__label">问题</span>
            <span class="field__value">{{ item.problem }}</span>
          </div>
          <div class="field">
            <span class="field__label">目标</span>
            <span class="field__value">
              {{ item.goal }}
              <el-tag v-if="item.goal_level" size="small" effect="plain" class="ml6">{{ item.goal_level }}</el-tag>
              <span v-if="item.outline.textbook_ref" class="field__sub">教材：{{ item.outline.textbook_ref }}</span>
            </span>
          </div>
          <div class="field">
            <span class="field__label">选择理由</span>
            <span class="field__value">{{ item.reason }}</span>
          </div>
          <div class="field">
            <span class="field__label">学习内容</span>
            <ul class="line-list">
              <li v-for="(c, i) in item.content" :key="i">{{ c }}</li>
            </ul>
          </div>
          <div class="field">
            <span class="field__label">练习安排</span>
            <div class="practice-list">
              <div v-for="p in item.practices" :key="p.stage" class="practice">
                <el-tag size="small" effect="plain">{{ p.stage }}</el-tag>
                <span class="practice__count">{{ p.count }} 题</span>
                <span class="practice__desc">{{ p.desc }}</span>
                <span class="practice__pass">达标线：{{ p.pass_line }}</span>
              </div>
            </div>
          </div>
          <div class="field">
            <span class="field__label">活动建议</span>
            <span class="field__value">{{ item.activity }}</span>
          </div>
          <div class="field">
            <span class="field__label">对应材料</span>
            <div class="material-list">
              <div v-for="(m, i) in item.materials" :key="i" class="material">
                <el-tag size="small" :type="materialTagType(m.kind)" effect="plain">{{ materialKindLabel(m.kind) }}</el-tag>
                <span class="material__title">{{ m.title }}</span>
                <span v-if="m.detail" class="material__detail">{{ m.detail }}</span>
                <span v-if="m.rule" class="material__rule">规则：{{ m.rule }}</span>
              </div>
            </div>
          </div>
          <div class="field">
            <span class="field__label">先后安排</span>
            <span class="field__value">{{ item.order_reason }}</span>
          </div>
          <div class="field">
            <span class="field__label">验收标准</span>
            <span class="field__value">{{ item.acceptance }}</span>
          </div>
          <div class="field field--tip">
            <span class="field__label">教师调整</span>
            <span class="field__value">{{ item.teacher_tip }}</span>
          </div>
        </div>
      </el-card>

      <!-- 补充观察 -->
      <el-card v-if="plan.observation_items.length" shadow="never" class="observation-card">
        <template #header>
          <div class="card-header">
            <span class="title">信息不足：先补充观察，再下结论</span>
            <el-tag size="small" type="info">{{ plan.observation_items.length }} 项</el-tag>
          </div>
        </template>
        <div v-for="(o, i) in plan.observation_items" :key="i" class="observation">
          <div class="observation__head">
            <span class="observation__kp">{{ o.knowledge_point }}</span>
            <span class="observation__evidence">{{ o.evidence }}</span>
          </div>
          <div class="observation__body">
            <p><span class="obs-label">建议</span>{{ o.action }}</p>
            <p><span class="obs-label">判断规则</span>{{ o.decision_rule }}</p>
            <p class="muted"><span class="obs-label">为什么</span>{{ o.reason }}</p>
          </div>
        </div>
      </el-card>

      <!-- 时间安排 -->
      <el-card v-if="plan.schedule.length" shadow="never" class="schedule-card">
        <template #header>
          <div class="card-header">
            <span class="title">时间安排</span>
            <el-tag size="small" type="info">共 {{ plan.duration_days }} 天</el-tag>
          </div>
        </template>
        <el-table :data="plan.schedule" size="small">
          <el-table-column label="第几天" width="90">
            <template #default="{ row }">第 {{ row.day }} 天</template>
          </el-table-column>
          <el-table-column label="对应步骤" width="120">
            <template #default="{ row }">
              {{ row.item_orders.length ? `第 ${row.item_orders.join('、')} 步` : '—' }}
            </template>
          </el-table-column>
          <el-table-column prop="knowledge_points" label="内容" min-width="180">
            <template #default="{ row }">{{ row.knowledge_points.join('、') }}</template>
          </el-table-column>
          <el-table-column label="时长" width="90">
            <template #default="{ row }">{{ row.minutes }} 分钟</template>
          </el-table-column>
          <el-table-column prop="note" label="说明" min-width="200" />
        </el-table>
      </el-card>

      <!-- 教师调整 + 数据说明 -->
      <el-card shadow="never" class="notes-card">
        <template #header>
          <div class="card-header">
            <span class="title">便于实施的说明</span>
          </div>
        </template>
        <div class="notes">
          <div class="notes__block">
            <div class="notes__title">给教师的调整建议</div>
            <ul class="line-list">
              <li v-for="(n, i) in plan.teacher_notes" :key="i">{{ n }}</li>
              <li v-if="!plan.teacher_notes.length" class="muted">暂无</li>
            </ul>
          </div>
          <div class="notes__block">
            <div class="notes__title">数据与口径说明</div>
            <ul class="line-list">
              <li v-for="(d, i) in plan.data_notes" :key="i">{{ d }}</li>
            </ul>
            <p class="muted small">
              生成引擎：{{ plan.engine }}；资源库检索 {{ plan.resources_checked || 0 }} 个文件；生成时间 {{ plan.generated_at.replace('T', ' ') }}
            </p>
          </div>
        </div>
      </el-card>

      <!-- 材料清单 -->
      <el-card v-if="plan.materials_index.length" shadow="never" class="materials-card">
        <template #header>
          <div class="card-header">
            <span class="title">材料清单（可追溯）</span>
            <el-tag size="small" type="info">{{ plan.materials_index.length }} 项</el-tag>
          </div>
        </template>
        <el-table :data="plan.materials_index" size="small">
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="materialTagType(row.kind)" effect="plain">{{ materialKindLabel(row.kind) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="材料 / 练习" min-width="220" />
          <el-table-column label="出处" width="120">
            <template #default="{ row }">{{ row.source || '—' }}</template>
          </el-table-column>
          <el-table-column label="用于" width="160">
            <template #default="{ row }">第 {{ row.order }} 步 · {{ row.for }}</template>
          </el-table-column>
          <el-table-column label="规则" min-width="220">
            <template #default="{ row }">{{ row.rule || '—' }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- ============ 历史方案 ============ -->
    <el-card shadow="never" class="history-card">
      <template #header>
        <div class="card-header">
          <span class="title">我的历史方案</span>
          <el-button link type="primary" size="small" @click="loadHistory">刷新</el-button>
        </div>
      </template>
      <el-table :data="history" size="small" empty-text="还没有生成过方案">
        <el-table-column prop="student_name" label="学生" width="110" />
        <el-table-column prop="course_name" label="课程" width="140" />
        <el-table-column prop="duration_days" label="周期" width="80">
          <template #default="{ row }">{{ row.duration_days }} 天</template>
        </el-table-column>
        <el-table-column prop="engine" label="引擎" width="120" />
        <el-table-column label="生成时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button link type="primary" @click="openPlan(row.id)">查看</el-button>
            <el-button link type="primary" @click="exportPlan(row.id, row.student_name, row.course_name)">导出</el-button>
            <el-button link type="danger" @click="removePlan(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ============ 导入：学生名单 ============ -->
    <FileImportDialog
      v-model="studentImportVisible"
      title="导入学生名单"
      :steps="STUDENT_IMPORT_STEPS"
      :field-rows="STUDENT_IMPORT_FIELDS"
      accept=".csv,.xlsx"
      accept-text="csv / xlsx"
      tip="支持 .csv / .xlsx，单文件不超过 5MB；邮箱重复的学生会跳过，坏行不入库"
      template-name="学生名单导入模板.csv"
      :download-template="learningAdviceApi.downloadStudentTemplate"
      :submit="doImportStudents"
      @imported="onStudentsImported"
    />

    <!-- ============ 导入：学情记录 ============ -->
    <FileImportDialog
      v-model="recordImportVisible"
      title="导入学情记录"
      :steps="RECORD_IMPORT_STEPS"
      :field-rows="RECORD_IMPORT_FIELDS"
      accept=".csv,.xlsx"
      accept-text="csv / xlsx"
      tip="按「学生姓名」匹配到已建号的学生；未建号的学生请先导入学生名单"
      template-name="学情导入模板.csv"
      :download-template="learningAnalysisApi.downloadImportTemplate"
      :submit="doImportRecords"
      @imported="onRecordsImported"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 个性化学习建议（任务3）
 * - 选择学生 → 生成方案（学情结论 + 课程大纲 + 资源）
 * - 建议条目给出：内容 / 练习 / 材料 / 理由 / 先后 / 验收 / 教师调整
 * - 学生信息与学情记录都可直接导入
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Download, MagicStick, Upload } from '@element-plus/icons-vue'
import FileImportDialog from '@/components/common/FileImportDialog.vue'
import type { ImportDialogResult, ImportFieldRow, ImportSummaryPart } from '@/components/common/importTypes'
import {
  learningAdviceApi,
  type AdviceCourse,
  type AdviceStudent,
  type LearningPlan,
  type PlanBrief,
  type StudentImportResult,
} from '@/services/learningAdvice'
import {
  learningAnalysisApi,
  type LearningImportResult,
} from '@/services/learningAnalysis'

const STUDENT_IMPORT_STEPS = [
  '下载模板，至少填写「姓名」一列；邮箱选填，留空会自动生成占位邮箱',
  '上传 .csv / .xlsx，系统逐行校验姓名与邮箱格式',
  '导入成功后学生出现在「学生」下拉里；要出建议还需导入该生的学情记录',
]

const STUDENT_IMPORT_FIELDS: ImportFieldRow[] = [
  { field: '姓名', required: '是', desc: '学生真实姓名，导入后作为昵称，用于与学情记录匹配' },
  { field: '邮箱', required: '否', desc: '用于登录；留空自动生成占位邮箱（该生暂不能登录，但可挂学情记录）' },
  { field: '年级', required: '否', desc: '如「2024级」「大二」' },
  { field: '专业', required: '否', desc: '如「计算机科学与技术」' },
  { field: '学校', required: '否', desc: '如「示例大学」' },
]

const RECORD_IMPORT_STEPS = [
  '下载模板，按表头填写成绩或答题记录；「学生姓名」要与已建号的学生一致',
  '上传 .csv / .xlsx，系统逐行校验学生、课程与字段',
  '导入成功后回到本页重新生成建议，结论会用上新数据',
]

const RECORD_IMPORT_FIELDS: ImportFieldRow[] = [
  { field: '学生姓名', required: '是', desc: '教师导入时按姓名匹配学生；没建号的学生请先导入学生名单' },
  { field: '课程', required: '否', desc: '课程名称或 ID，如「数据结构」' },
  { field: '知识点', required: '是', desc: '如「排序」「图的遍历」，个性化建议按此对齐大纲内容' },
  { field: '记录类型', required: '否', desc: '测验 / 作业 / 考试 / 练习' },
  { field: '对错', required: '否', desc: '对 / 错，也识别 正确/错误、Y/N、1/0' },
  { field: '得分 / 满分', required: '否', desc: '数值，如 85 / 100' },
  { field: '记录时间', required: '否', desc: '如 2026-01-08 09:30，留空按导入时间' },
]

const courses = ref<AdviceCourse[]>([])
const students = ref<AdviceStudent[]>([])
const courseId = ref<number>()
const studentId = ref<number>()
const durationDays = ref(7)
const focus = ref('')

const loadingStudents = ref(false)
const generating = ref(false)
const plan = ref<LearningPlan | null>(null)
const history = ref<PlanBrief[]>([])

const studentImportVisible = ref(false)
const recordImportVisible = ref(false)

const outlineHint = computed(() => {
  const s = students.value.find((x) => x.student_id === studentId.value)
  if (s && !s.record_count) return '该生暂无学情记录，将生成「补充观察」型方案'
  return ''
})

function materialKindLabel(kind: string): string {
  return { textbook: '教材', resource: '资源库', rule: '按规则登记' }[kind] ?? kind
}

function materialTagType(kind: string): 'success' | 'warning' | 'info' {
  return kind === 'textbook' ? 'success' : kind === 'resource' ? 'warning' : 'info'
}

function formatTime(v?: string): string {
  if (!v) return '—'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN')
}

async function loadCourses(): Promise<void> {
  courses.value = await learningAdviceApi.courses()
  if (!courseId.value && courses.value.length) {
    const ds = courses.value.find((c) => c.name.includes('数据结构'))
    courseId.value = ds?.id ?? courses.value[0].id
  }
}

async function loadStudents(): Promise<void> {
  loadingStudents.value = true
  try {
    students.value = await learningAdviceApi.students(courseId.value)
    if (!students.value.some((s) => s.student_id === studentId.value)) {
      studentId.value = students.value.find((s) => s.record_count > 0)?.student_id
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载学生列表失败')
  } finally {
    loadingStudents.value = false
  }
}

async function loadHistory(): Promise<void> {
  try {
    history.value = await learningAdviceApi.plans()
  } catch {
    history.value = []
  }
}

async function onCourseChange(): Promise<void> {
  plan.value = null
  await loadStudents()
}

async function onGenerate(): Promise<void> {
  if (!studentId.value) {
    ElMessage.warning('请先选择学生')
    return
  }
  generating.value = true
  try {
    plan.value = await learningAdviceApi.generate({
      student_id: studentId.value,
      course_id: courseId.value,
      duration_days: durationDays.value,
      focus: focus.value.trim() || undefined,
    })
    ElMessage.success('建议已生成')
    await loadHistory()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e: any) {
    ElMessage.error(e?.message || '生成失败，请稍后重试')
  } finally {
    generating.value = false
  }
}

async function openPlan(id: number): Promise<void> {
  try {
    plan.value = await learningAdviceApi.plan(id)
    durationDays.value = plan.value.duration_days
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e: any) {
    ElMessage.error(e?.message || '方案加载失败')
  }
}

async function onExport(): Promise<void> {
  if (!plan.value?.plan_id) return
  await exportPlan(plan.value.plan_id, plan.value.student.name, plan.value.course.name)
}

async function exportPlan(id: number, studentName?: string, courseName?: string): Promise<void> {
  try {
    await learningAdviceApi.downloadPlan(id, `${studentName || '学生'}-${courseName || '课程'}-个性化学习建议.md`)
    ElMessage.success('已导出 Markdown')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  }
}

async function removePlan(id: number): Promise<void> {
  try {
    await ElMessageBox.confirm('确定删除这份方案吗？删除后不可恢复。', '删除方案', { type: 'warning' })
  } catch {
    return
  }
  try {
    await learningAdviceApi.remove(id)
    ElMessage.success('已删除')
    if (plan.value?.plan_id === id) plan.value = null
    await loadHistory()
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
}

function onImportCommand(cmd: string): void {
  if (cmd === 'students') studentImportVisible.value = true
  else recordImportVisible.value = true
}

async function doImportStudents(file: File): Promise<ImportDialogResult> {
  const res: StudentImportResult = await learningAdviceApi.importStudents(file)
  const summary: ImportSummaryPart[] = [
    { text: `文件共 ${res.total} 行`, tone: 'muted' },
    { text: `新增 ${res.created} 人`, tone: res.created ? 'ok' : 'bad' },
  ]
  if (res.skipped) summary.push({ text: `已存在跳过 ${res.skipped} 人`, tone: 'warn' })
  if (res.failed) summary.push({ text: `未通过校验 ${res.failed} 行`, tone: 'bad' })
  if (res.default_password && res.created) {
    summary.push({ text: `默认登录密码 ${res.default_password}`, tone: 'muted' })
  }

  let title: string
  let tone: ImportDialogResult['tone']
  if (!res.created && !res.skipped) {
    title = '没有导入任何学生，请按下方原因修正后重试'
    tone = 'error'
  } else if (res.failed) {
    title = `新增 ${res.created} 人，${res.failed} 行未通过校验`
    tone = 'warning'
  } else if (!res.created && res.skipped) {
    title = `没有新增学生：${res.skipped} 人已存在`
    tone = 'warning'
  } else {
    title = `成功新增 ${res.created} 名学生`
    tone = 'success'
  }

  return { title, tone, summary, errors: res.errors, payload: res }
}

async function onStudentsImported(result: ImportDialogResult): Promise<void> {
  const payload = result.payload as StudentImportResult | undefined
  if (!payload?.created) return
  await loadStudents()
}

async function doImportRecords(file: File): Promise<ImportDialogResult> {
  const res: LearningImportResult = await learningAnalysisApi.importRecords(file)
  const summary: ImportSummaryPart[] = [
    { text: `文件共 ${res.total_rows} 行`, tone: 'muted' },
    { text: `成功 ${res.imported} 条`, tone: res.imported ? 'ok' : 'bad' },
  ]
  if (res.failed) summary.push({ text: `未通过校验 ${res.failed} 行`, tone: 'bad' })
  let title: string
  let tone: ImportDialogResult['tone']
  if (!res.imported) {
    title = '没有导入任何记录，请按下方原因修正文件后重试'
    tone = 'error'
  } else if (res.failed) {
    title = `已导入 ${res.imported} 条，${res.failed} 行未通过校验`
    tone = 'warning'
  } else {
    title = `成功导入 ${res.imported} 条记录`
    tone = 'success'
  }
  return { title, tone, summary, errors: res.errors, errorsTruncated: res.errors_truncated, payload: res }
}

async function onRecordsImported(result: ImportDialogResult): Promise<void> {
  const payload = result.payload as LearningImportResult | undefined
  if (!payload?.imported) return
  await loadStudents()
  ElMessage.info('学情数据已更新，重新点「生成」即可用上新数据')
}

onMounted(async () => {
  try {
    await loadCourses()
    await loadStudents()
    await loadHistory()
  } catch (e: any) {
    ElMessage.error(e?.message || '页面初始化失败')
  }
})
</script>

<style lang="scss" scoped>
.advice-view {
  padding: 4px 0 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 14px;

  &__left {
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-wrap: wrap;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
      white-space: nowrap;
    }
  }

  &__hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  &__actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

.control-card {
  margin-bottom: 14px;

  :deep(.el-card__body) {
    padding-bottom: 6px;
  }
}

.control-form {
  :deep(.el-form-item) {
    margin-bottom: 10px;
    margin-right: 16px;
  }
}

.control-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.7;
  padding-bottom: 8px;

  &__warn {
    color: var(--el-color-warning);
  }
}

.empty-card,
.summary-card,
.step-card,
.observation-card,
.schedule-card,
.notes-card,
.materials-card,
.history-card {
  margin-bottom: 14px;
}

.empty-desc {
  p {
    margin: 4px 0;
    font-size: 13px;

    &.muted {
      color: var(--el-text-color-secondary);
    }
  }
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;

  &__title {
    font-size: 16px;
    font-weight: 600;
    margin-right: 8px;
  }

  &__tag {
    margin-right: 6px;
  }
}

.stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 14px 0;
}

.stat {
  flex: 1 1 110px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px 12px;

  &__value {
    font-size: 20px;
    font-weight: 700;
    color: var(--el-color-primary);

    &--warn {
      color: var(--el-color-warning);
    }
  }

  &__label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 2px;
  }
}

.goal-box {
  border-left: 3px solid var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 10px 12px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.7;

  &__label {
    font-weight: 600;
    margin-right: 8px;
  }
}

.step-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;

  &__no {
    font-weight: 600;
    color: var(--el-color-primary);
  }

  &__kp {
    font-size: 15px;
    font-weight: 600;
  }

  &__acc,
  &__min {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

.step-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field {
  display: flex;
  gap: 12px;
  font-size: 13px;
  line-height: 1.75;

  &__label {
    flex: 0 0 74px;
    color: var(--el-text-color-secondary);
    font-size: 12px;
    padding-top: 1px;
  }

  &__value {
    flex: 1;
    min-width: 0;
  }

  &__sub {
    display: block;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  &--tip {
    background: var(--el-color-info-light-9);
    border-radius: 6px;
    padding: 8px 10px;
  }
}

.ml6 {
  margin-left: 6px;
}

.line-list {
  margin: 0;
  padding-left: 18px;

  li {
    margin: 2px 0;
  }
}

.practice-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.practice {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  padding: 6px 10px;

  &__count {
    font-weight: 600;
  }

  &__desc {
    flex: 1;
    min-width: 160px;
  }

  &__pass {
    font-size: 12px;
    color: var(--el-color-warning);
  }
}

.material-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.material {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;

  &__title {
    font-weight: 500;
  }

  &__detail,
  &__rule {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

.observation {
  border-left: 3px solid var(--el-color-info);
  padding: 8px 0 8px 12px;
  margin-bottom: 10px;

  &__head {
    display: flex;
    gap: 10px;
    align-items: baseline;
    flex-wrap: wrap;
    margin-bottom: 4px;
  }

  &__kp {
    font-weight: 600;
  }

  &__evidence {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  &__body p {
    margin: 3px 0;
    font-size: 13px;
    line-height: 1.7;
  }
}

.obs-label {
  display: inline-block;
  min-width: 62px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-right: 6px;
}

.notes {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;

  &__block {
    flex: 1 1 320px;
    min-width: 260px;
  }

  &__title {
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 6px;
  }
}

.muted {
  color: var(--el-text-color-secondary);
}

.small {
  font-size: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;

  .title {
    font-weight: 600;
  }
}

.stu-option__name {
  margin-right: 8px;
}

.stu-option__meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
