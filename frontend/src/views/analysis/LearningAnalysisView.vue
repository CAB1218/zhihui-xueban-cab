<template>
  <div class="analysis-page" v-loading="loading">
    <!-- 顶部 -->
    <div class="page-header">
      <div class="page-header__left">
        <h2>学情分析</h2>
        <span class="page-header__sub">数据质量检查 · 个体与群体学习情况摘要</span>
      </div>
      <div class="page-header__right">
        <el-select v-model="courseId" placeholder="选择课程" clearable style="width: 180px" @change="reloadAll">
          <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-dropdown trigger="click" @command="onExport">
          <el-button type="primary">
            导出报告<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="group-md">班级报告（Markdown）</el-dropdown-item>
              <el-dropdown-item command="group-docx">班级报告（Word）</el-dropdown-item>
              <el-dropdown-item command="individual-md" :disabled="!selectedStudentId">
                个人报告（Markdown）
              </el-dropdown-item>
              <el-dropdown-item command="individual-docx" :disabled="!selectedStudentId">
                个人报告（Word）
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <el-alert v-if="overview?.is_simulated" type="warning" :closable="false" show-icon class="sim-alert">
      <template #title>
        本页数据为<strong>模拟学情数据</strong>（{{ overview.simulated_count }} 条），用于演示分析流程。
        数据中刻意保留了真实采集中常见的缺失、异常与重复，下方的质量检查会说明每类问题如何识别与处理。
      </template>
    </el-alert>

    <!-- 概览 -->
    <el-row :gutter="14" class="stat-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-card__value">{{ overview?.records_total ?? '-' }}</div>
          <div class="stat-card__label">原始记录</div>
          <div class="stat-card__hint">含缺失/异常/重复</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card stat-card--ok">
          <div class="stat-card__value">{{ overview?.records_valid ?? '-' }}</div>
          <div class="stat-card__label">有效记录</div>
          <div class="stat-card__hint">剔除 {{ overview?.records_excluded ?? 0 }} 条后</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-card__value">{{ overview?.students ?? '-' }}</div>
          <div class="stat-card__label">覆盖学生</div>
          <div class="stat-card__hint">{{ overview?.courses ?? 0 }} 门课程</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card stat-card--accent">
          <div class="stat-card__value">{{ pct(overview?.accuracy) }}</div>
          <div class="stat-card__label">整体正确率</div>
          <div class="stat-card__hint">{{ overview?.judgeable ?? 0 }} 次可判断作答</div>
        </div>
      </el-col>
    </el-row>

    <!-- 质量检查 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-head">
          <span class="card-head__title">数据整理与质量检查</span>
          <div class="card-head__tags">
            <el-tag type="warning" effect="plain" size="small">缺失 {{ quality?.counts.missing ?? 0 }}</el-tag>
            <el-tag type="danger" effect="plain" size="small">异常 {{ quality?.counts.abnormal ?? 0 }}</el-tag>
            <el-tag type="info" effect="plain" size="small">重复 {{ quality?.counts.duplicate ?? 0 }}</el-tag>
          </div>
        </div>
      </template>

      <el-table :data="quality?.issues ?? []" size="small" border class="issue-table">
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.type)" size="small" effect="plain">{{ typeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="问题" width="220" />
        <el-table-column prop="count" label="条数" width="70" align="right" />
        <el-table-column prop="handling" label="处理方式" min-width="300" />
        <el-table-column label="处理" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="handlingTag(row.handling_type)">{{ row.handling_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="" width="60" align="center">
          <template #default="{ row }">
            <el-popover placement="left" :width="380" trigger="click">
              <template #reference>
                <el-button link type="primary" size="small">详情</el-button>
              </template>
              <div class="pop-detail">
                <p class="pop-detail__reason">{{ row.detail }}</p>
                <p class="pop-detail__ids">
                  示例记录：<code v-for="id in row.record_ids.slice(0, 8)" :key="id">#{{ id }} </code>
                  <span v-if="row.record_ids.length > 8">等 {{ row.count }} 条</span>
                </p>
              </div>
            </el-popover>
          </template>
        </el-table-column>
      </el-table>

      <div class="steps-line">
        <span class="steps-line__label">处理流程</span>
        <template v-for="(s, i) in quality?.steps ?? []" :key="i">
          <span class="steps-line__item">
            {{ s.step }}
            <b>{{ s.before }}</b> → <b>{{ s.after }}</b>
            <em v-if="s.removed">(-{{ s.removed }})</em>
          </span>
          <el-icon v-if="i < (quality?.steps.length ?? 0) - 1" class="steps-line__arrow"><Right /></el-icon>
        </template>
      </div>

      <div class="notes">
        <p v-for="(n, i) in quality?.notes ?? []" :key="i">· {{ n }}</p>
      </div>
    </el-card>

    <!-- 主体 -->
    <el-tabs v-model="tab" class="main-tabs">
      <!-- ============ 个体 ============ -->
      <el-tab-pane label="个体分析" name="individual">
        <div class="ind-toolbar">
          <span class="ind-toolbar__label">选择学生</span>
          <el-select
            v-model="selectedStudentId"
            filterable
            placeholder="按姓名搜索"
            style="width: 260px"
            @change="loadIndividual"
          >
            <el-option
              v-for="s in students"
              :key="s.student_id"
              :label="`${s.name}（${s.judgeable_count} 次可判断）`"
              :value="s.student_id"
            />
          </el-select>
          <el-tag v-if="individual?.student.major" size="small" type="info">{{ individual.student.major }}</el-tag>
          <el-tag v-if="individual?.course_name" size="small" type="info">{{ individual.course_name }}</el-tag>
        </div>

        <template v-if="individual">
          <el-row :gutter="14" class="stat-row">
            <el-col :xs="12" :sm="6">
              <div class="mini-stat">
                <div class="mini-stat__v">{{ individual.overall.attempts }}</div>
                <div class="mini-stat__l">可判断作答</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="mini-stat">
                <div class="mini-stat__v">{{ pct(individual.overall.accuracy) }}</div>
                <div class="mini-stat__l">个人正确率</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="mini-stat">
                <div class="mini-stat__v">{{ individual.overall.knowledge_point_count }}</div>
                <div class="mini-stat__l">涉及知识点</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="mini-stat">
                <div class="mini-stat__v">{{ individual.overall.practice_days }}</div>
                <div class="mini-stat__l">练习跨度（天）</div>
              </div>
            </el-col>
          </el-row>

          <el-alert type="info" :closable="false" class="basis-alert">
            <template #title>
              正确率口径：{{ individual.overall.accuracy_basis }}；判定门槛为同一知识点作答 ≥
              {{ individual.thresholds.min_attempts }} 次。
            </template>
          </el-alert>

          <el-row :gutter="14">
            <el-col :xs="24" :lg="14">
              <el-card shadow="never" class="section-card">
                <template #header><span class="card-head__title">各知识点表现</span></template>
                <el-table :data="individual.knowledge_points" size="small" border>
                  <el-table-column prop="knowledge_point" label="知识点" min-width="120" />
                  <el-table-column prop="attempts" label="作答" width="64" align="right" />
                  <el-table-column label="正确率" width="110" align="right">
                    <template #default="{ row }">
                      <span :class="accClass(row.accuracy)">{{ pct(row.accuracy) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="判断" width="150">
                    <template #default="{ row }">
                      <el-tooltip :content="row.evidence_text" placement="top">
                        <el-tag :type="statusTag(row.status)" size="small">{{ row.status_label }}</el-tag>
                      </el-tooltip>
                    </template>
                  </el-table-column>
                  <el-table-column label="证据记录" min-width="120">
                    <template #default="{ row }">
                      <span class="ids">#{{ row.evidence_record_ids.slice(0, 5).join(' #') }}</span>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>

            <el-col :xs="24" :lg="10">
              <el-card shadow="never" class="section-card">
                <template #header>
                  <span class="card-head__title">需要巩固的内容</span>
                  <el-tag v-if="individual.needs_consolidation.length" type="warning" size="small" class="ml8">
                    {{ individual.needs_consolidation.length }} 项
                  </el-tag>
                </template>
                <div v-if="individual.needs_consolidation.length" class="kp-list">
                  <div v-for="k in individual.needs_consolidation" :key="k.knowledge_point" class="kp-item kp-item--warn">
                    <div class="kp-item__name">{{ k.knowledge_point }}</div>
                    <div class="kp-item__meta">{{ k.evidence_text }}</div>
                    <div class="kp-item__ids">依据：<code>#{{ k.evidence_record_ids.slice(0, 4).join(' #') }}</code></div>
                  </div>
                </div>
                <el-empty v-else description="没有达到“需巩固”判定条件的知识点" :image-size="56" />
              </el-card>

              <el-card v-if="individual.fair_areas.length" shadow="never" class="section-card">
                <template #header><span class="card-head__title">基本掌握、建议适度巩固</span></template>
                <div class="kp-list">
                  <div v-for="k in individual.fair_areas" :key="k.knowledge_point" class="kp-item kp-item--fair">
                    <div class="kp-item__name">{{ k.knowledge_point }}</div>
                    <div class="kp-item__meta">{{ k.evidence_text }}</div>
                  </div>
                </div>
              </el-card>

              <el-card shadow="never" class="section-card">
                <template #header>
                  <span class="card-head__title">已掌握较好</span>
                </template>
                <div v-if="individual.strengths.length" class="kp-list">
                  <div v-for="k in individual.strengths" :key="k.knowledge_point" class="kp-item kp-item--good">
                    <div class="kp-item__name">{{ k.knowledge_point }}</div>
                    <div class="kp-item__meta">{{ k.evidence_text }}</div>
                  </div>
                </div>
                <el-empty v-else description="暂无稳定达到掌握良好水平的知识点" :image-size="56" />
              </el-card>
            </el-col>
          </el-row>

          <el-card v-if="individual.insufficient_evidence.length" shadow="never" class="section-card insufficient-card">
            <template #header>
              <span class="card-head__title">信息不足、尚不能判断的内容</span>
            </template>
            <p class="insufficient-intro">
              以下知识点的作答次数少于 <b>{{ individual.thresholds.min_attempts }}</b> 次，样本不足以判断掌握情况。
              <b>「记录少」不等于「没学会」</b>，可能是练习安排较少或数据未采集完整，需要补做练习后再判断。
            </p>
            <div class="insufficient-list">
              <el-tag v-for="k in individual.insufficient_evidence" :key="k.knowledge_point" type="info" effect="plain">
                {{ k.knowledge_point }}（仅 {{ k.attempts }} 次）
              </el-tag>
            </div>
          </el-card>

          <el-card shadow="never" class="section-card">
            <template #header><span class="card-head__title">数据说明</span></template>
            <ul class="note-list">
              <li v-for="(n, i) in individual.data_notes" :key="i">{{ n }}</li>
            </ul>
          </el-card>
        </template>
        <el-empty v-else description="请选择一名学生查看分析" />
      </el-tab-pane>

      <!-- ============ 群体 ============ -->
      <el-tab-pane label="群体分析" name="group">
        <template v-if="group">
          <el-row :gutter="14" class="stat-row">
            <el-col :xs="12" :sm="6">
              <div class="mini-stat">
                <div class="mini-stat__v">{{ group.cohort.students_total }}</div>
                <div class="mini-stat__l">参与学生</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="mini-stat">
                <div class="mini-stat__v">{{ group.cohort.total_attempts }}</div>
                <div class="mini-stat__l">累计作答</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="mini-stat">
                <div class="mini-stat__v">{{ pct(group.overall.accuracy) }}</div>
                <div class="mini-stat__l">整体正确率</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="mini-stat">
                <div class="mini-stat__v">{{ group.cohort.avg_attempts }}</div>
                <div class="mini-stat__l">人均作答</div>
              </div>
            </el-col>
          </el-row>

          <el-alert type="info" :closable="false" class="basis-alert">
            <template #title>
              {{ group.cohort.students_judged }} 人有可判断记录，其中
              <b>{{ group.cohort.students_reliable }}</b> 人可用于横向比较<template
                v-if="group.cohort.students_sparse"
              >；另有 {{ group.cohort.students_sparse }} 人作答量不足，单独说明、不参与排名</template>。
            </template>
          </el-alert>

          <el-row :gutter="14">
            <el-col :xs="24" :lg="12">
              <el-card shadow="never" class="section-card">
                <template #header>
                  <span class="card-head__title">共性问题（多名学生同时薄弱）</span>
                </template>
                <div v-if="group.common_weak_points.length" class="weak-list">
                  <div v-for="k in group.common_weak_points" :key="k.knowledge_point" class="weak-item">
                    <div class="weak-item__head">
                      <span class="weak-item__name">{{ k.knowledge_point }}</span>
                      <el-tag type="danger" size="small">{{ pct(k.accuracy) }}</el-tag>
                    </div>
                    <el-progress
                      :percentage="Math.round(k.weak_ratio * 100)"
                      :stroke-width="8"
                      status="exception"
                      :format="() => `薄弱 ${k.weak_students}/${k.students_practiced} 人`"
                    />
                    <div class="weak-item__basis">{{ k.evidence_text }}</div>
                  </div>
                </div>
                <el-empty
                  v-else
                  :description="`按当前口径（≥${group.thresholds.common_weak_ratio * 100}% 学生低于 ${group.thresholds.acc_weak * 100}%）未发现共性问题`"
                  :image-size="56"
                />
              </el-card>
            </el-col>

            <el-col :xs="24" :lg="12">
              <el-card shadow="never" class="section-card">
                <template #header><span class="card-head__title">值得关注的差异</span></template>
                <div v-if="group.differences.accuracy" class="diff-block">
                  <div class="diff-row">
                    <span class="diff-row__l">正确率跨度</span>
                    <span class="diff-row__v">
                      {{ pct(group.differences.accuracy.min) }} ~ {{ pct(group.differences.accuracy.max) }}
                      <em>（{{ (group.differences.accuracy.gap * 100).toFixed(1) }} 个百分点）</em>
                    </span>
                  </div>
                  <div class="diff-row">
                    <span class="diff-row__l">标准差</span>
                    <span class="diff-row__v">{{ group.differences.accuracy.std.toFixed(3) }}</span>
                  </div>
                  <div class="diff-row" v-if="group.differences.attempts">
                    <span class="diff-row__l">练习量</span>
                    <span class="diff-row__v">{{ group.differences.attempts.evidence_text }}</span>
                  </div>
                  <p class="diff-basis">{{ group.differences.accuracy.evidence_text }}</p>
                </div>

                <div v-if="group.notable_cases.length" class="notable">
                  <div
                    v-for="(n, i) in group.notable_cases"
                    :key="i"
                    :class="['notable-item', n.type === 'insufficient' ? 'notable-item--info' : 'notable-item--warn']"
                  >
                    <el-tag :type="n.type === 'insufficient' ? 'info' : 'warning'" size="small">
                      {{ n.type === 'insufficient' ? '样本不足' : '需关注' }}
                    </el-tag>
                    <span class="notable-item__name">{{ n.student_name }}</span>
                    <span class="notable-item__note">{{ n.note }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-card shadow="never" class="section-card">
            <template #header><span class="card-head__title">分析维度与实际数据的匹配情况</span></template>
            <p class="dim-intro">
              分析维度以实际采集到的字段为准。数据未采集的维度不强行分析，避免给出没有依据的结论。
            </p>
            <el-table :data="group.dimension_check" size="small" border>
              <el-table-column prop="dimension" label="分析维度" width="200" />
              <el-table-column label="数据可用率" width="140" align="right">
                <template #default="{ row }">{{ (row.available_ratio * 100).toFixed(0) }}%</template>
              </el-table-column>
              <el-table-column label="是否采用" width="110" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.usable ? 'success' : 'info'" size="small">
                    {{ row.usable ? '采用' : '不采用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="note" label="说明" min-width="300" />
            </el-table>
          </el-card>

          <el-card shadow="never" class="section-card">
            <template #header><span class="card-head__title">各知识点整体表现</span></template>
            <el-table :data="group.knowledge_points" size="small" border>
              <el-table-column prop="knowledge_point" label="知识点" min-width="130" />
              <el-table-column prop="students_practiced" label="作答人数" width="90" align="right" />
              <el-table-column prop="attempts" label="作答次数" width="90" align="right" />
              <el-table-column label="整体正确率" width="110" align="right">
                <template #default="{ row }">
                  <span :class="accClass(row.accuracy)">{{ pct(row.accuracy) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="薄弱人数" width="150">
                <template #default="{ row }">
                  {{ row.weak_students }} / {{ row.students_practiced }}
                  <el-tag v-if="row.is_common_weak" type="danger" size="small" effect="plain" class="ml6">共性</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="section-card">
            <template #header><span class="card-head__title">数据说明</span></template>
            <ul class="note-list">
              <li v-for="(n, i) in group.data_notes" :key="i">{{ n }}</li>
            </ul>
          </el-card>
        </template>
        <el-empty v-else description="暂无群体分析数据" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, Right } from '@element-plus/icons-vue'
import {
  learningAnalysisApi,
  type GroupReport,
  type IndividualReport,
  type Overview,
  type QualityResult,
  type StudentBrief,
} from '@/services/learningAnalysis'
import api from '@/services/api'

const loading = ref(false)
const tab = ref<'individual' | 'group'>('group')

const overview = ref<Overview | null>(null)
const quality = ref<QualityResult | null>(null)
const students = ref<StudentBrief[]>([])
const individual = ref<IndividualReport | null>(null)
const group = ref<GroupReport | null>(null)

const courseId = ref<number | undefined>(undefined)
const selectedStudentId = ref<number | undefined>(undefined)
const courses = ref<Array<{ id: number; name: string }>>([])

function pct(v?: number | null): string {
  if (v === null || v === undefined) return '—'
  return `${(v * 100).toFixed(1)}%`
}

function accClass(v: number): string {
  if (v >= 0.8) return 'acc acc--good'
  if (v >= 0.6) return 'acc acc--fair'
  return 'acc acc--weak'
}

function typeLabel(t: string): string {
  return { missing: '缺失', abnormal: '异常', duplicate: '重复' }[t] ?? t
}

function typeTag(t: string): 'warning' | 'danger' | 'info' {
  return t === 'missing' ? 'warning' : t === 'abnormal' ? 'danger' : 'info'
}

function handlingTag(t: string): 'danger' | 'success' | 'warning' | 'primary' {
  if (t === '剔除') return 'danger'
  if (t === '合并') return 'warning'
  if (t === '修正') return 'primary'
  return 'success'
}

function statusTag(s: string): 'success' | 'primary' | 'warning' | 'info' {
  return { good: 'success', fair: 'primary', needs_work: 'warning', insufficient: 'info' }[
    s
  ] as 'success' | 'primary' | 'warning' | 'info'
}

async function loadCourses() {
  try {
    const res: any = await api.get('/teachers/courses')
    const list = (res?.data ?? res) as any[]
    courses.value = Array.isArray(list) ? list.map((c) => ({ id: c.id, name: c.name })) : []
    if (!courseId.value && courses.value.length) {
      const cs = courses.value.find((c) => c.name.includes('数据结构'))
      courseId.value = cs?.id ?? courses.value[0].id
    }
  } catch {
    courses.value = []
  }
}

async function loadOverviewAndQuality() {
  const [o, q] = await Promise.all([
    learningAnalysisApi.overview(courseId.value),
    learningAnalysisApi.quality(courseId.value),
  ])
  overview.value = o
  quality.value = q
}

async function loadGroup() {
  try {
    group.value = await learningAnalysisApi.group(courseId.value)
  } catch (e: any) {
    group.value = null
  }
}

async function loadIndividual() {
  if (!selectedStudentId.value) {
    individual.value = null
    return
  }
  try {
    individual.value = await learningAnalysisApi.individual(selectedStudentId.value, courseId.value)
  } catch (e: any) {
    individual.value = null
    ElMessage.warning(e?.message || '该学生暂无可用记录')
  }
}

async function reloadAll() {
  loading.value = true
  try {
    await loadOverviewAndQuality()
    await Promise.all([loadGroup(), loadIndividual()])
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function onExport(cmd: string) {
  const [kind, format] = cmd.split('-') as ['group' | 'individual', 'md' | 'docx']
  if (kind === 'individual' && !selectedStudentId.value) {
    ElMessage.warning('请先选择学生')
    return
  }
  try {
    const blob = await learningAnalysisApi.exportReport({
      kind,
      courseId: courseId.value,
      studentId: kind === 'individual' ? selectedStudentId.value : undefined,
      format,
    })
    const name =
      kind === 'group'
        ? `${overview.value?.course?.name || '班级'}学情分析.${format}`
        : `${individual.value?.student.name || '学生'}学情分析.${format}`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('报告已导出')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await loadCourses()
    await loadOverviewAndQuality()
    students.value = await learningAnalysisApi.students()
    const first = students.value[0]
    if (first) {
      selectedStudentId.value = first.student_id
    }
    await Promise.all([loadGroup(), loadIndividual()])
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.analysis-page {
  padding: 4px 2px 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.page-header__left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-header__left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.page-header__sub {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.page-header__right {
  display: flex;
  gap: 10px;
  align-items: center;
}

.sim-alert {
  margin-bottom: 14px;
}

.stat-row {
  margin-bottom: 14px;
}

.stat-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 14px 16px;
  height: 100%;
}

.stat-card__value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--el-text-color-primary);
}

.stat-card__label {
  font-size: 13px;
  color: var(--el-text-color-regular);
  margin-top: 2px;
}

.stat-card__hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  margin-top: 4px;
}

.stat-card--ok .stat-card__value {
  color: var(--el-color-success);
}

.stat-card--accent .stat-card__value {
  color: var(--el-color-primary);
}

.section-card {
  margin-bottom: 14px;
  border-radius: 10px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-head__title {
  font-weight: 600;
  font-size: 15px;
}

.card-head__tags {
  display: flex;
  gap: 6px;
}

.issue-table {
  margin-bottom: 12px;
}

.pop-detail__reason {
  margin: 0 0 8px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}

.pop-detail__ids {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.pop-detail code {
  background: var(--el-fill-color-light);
  padding: 1px 4px;
  border-radius: 3px;
  margin-right: 2px;
}

.steps-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  font-size: 13px;
}

.steps-line__label {
  font-weight: 600;
  margin-right: 6px;
  color: var(--el-text-color-regular);
}

.steps-line__item b {
  color: var(--el-text-color-primary);
}

.steps-line__item em {
  color: var(--el-color-danger);
  font-style: normal;
  margin-left: 2px;
}

.steps-line__arrow {
  color: var(--el-text-color-placeholder);
}

.notes {
  margin-top: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.8;
}

.main-tabs {
  margin-top: 4px;
}

.ind-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.ind-toolbar__label {
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.mini-stat {
  background: var(--el-fill-color-lighter);
  border-radius: 10px;
  padding: 12px 14px;
  text-align: center;
  height: 100%;
}

.mini-stat__v {
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.mini-stat__l {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.basis-alert {
  margin-bottom: 14px;
}

.acc {
  font-weight: 600;
}

.acc--good {
  color: var(--el-color-success);
}

.acc--fair {
  color: var(--el-color-primary);
}

.acc--weak {
  color: var(--el-color-danger);
}

.ids {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-family: monospace;
}

.kp-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kp-item {
  border-left: 3px solid var(--el-border-color);
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.kp-item--warn {
  border-left-color: var(--el-color-warning);
}

.kp-item--fair {
  border-left-color: var(--el-color-primary);
}

.kp-item--good {
  border-left-color: var(--el-color-success);
}

.kp-item__name {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 2px;
}

.kp-item__meta {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.kp-item__ids {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  margin-top: 3px;
}

.insufficient-card :deep(.el-card__body) {
  padding-top: 8px;
}

.insufficient-intro {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.8;
  margin: 0 0 10px;
}

.insufficient-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.note-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.9;
}

.weak-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.weak-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.weak-item__name {
  font-weight: 600;
  font-size: 14px;
}

.weak-item__basis {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 6px;
}

.diff-block {
  margin-bottom: 12px;
}

.diff-row {
  display: flex;
  justify-content: space-between;
  padding: 7px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  font-size: 13px;
}

.diff-row__l {
  color: var(--el-text-color-secondary);
}

.diff-row__v {
  color: var(--el-text-color-primary);
  font-weight: 500;
}

.diff-row__v em {
  font-style: normal;
  color: var(--el-text-color-secondary);
  font-weight: 400;
}

.diff-basis {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 10px 0 0;
  line-height: 1.7;
}

.notable {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notable-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.7;
}

.notable-item--warn {
  background: var(--el-color-warning-light-9);
}

.notable-item--info {
  background: var(--el-fill-color-light);
}

.notable-item__name {
  font-weight: 600;
  white-space: nowrap;
}

.notable-item__note {
  color: var(--el-text-color-regular);
}

.dim-intro {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0 0 10px;
}

.ml6 {
  margin-left: 6px;
}

.ml8 {
  margin-left: 8px;
}
</style>
