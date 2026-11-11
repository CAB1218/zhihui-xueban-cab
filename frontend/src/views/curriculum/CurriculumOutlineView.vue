<template>
  <div class="curriculum-page">
    <el-card shadow="never" class="input-card">
      <template #header>
        <div class="card-header">
          <span class="title">📚 课程梳理（理解学科 — 学习内容与要求梳理）</span>
          <div class="actions">
            <el-tag v-if="record?.outline?.is_sample" type="warning" size="small">离线梳理结果</el-tag>
            <el-button type="primary" plain size="small" :icon="Upload" @click="showImport = true">
              导入大纲/课表
            </el-button>
          </div>
        </div>
      </template>

      <el-form :model="form" label-width="90px" @submit.prevent="onGenerate">
        <el-form-item label="想学课程" required>
          <div class="course-input">
            <el-input
              v-model="form.course_query"
              placeholder="例如：数据结构 / 初中数学七年级上册 / 高等数学（可先点下方示例快速填入）"
              clearable
              @keyup.enter="onGenerate"
            />
            <div class="quick-picks">
              <span class="quick-label">快速示例：</span>
              <el-tag
                v-for="p in QUICK_PICKS"
                :key="p.course"
                size="small"
                effect="plain"
                class="quick-tag"
                @click="fillQuick(p)"
              >{{ p.label }}</el-tag>
            </div>
          </div>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="学段年级">
              <el-input v-model="form.grade_level" placeholder="如：七年级 / 高一 / 大二（可留空）" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学科">
              <el-select v-model="form.subject" placeholder="留空自动识别" clearable style="width: 100%">
                <el-option v-for="s in SUBJECTS" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="联网检索">
              <el-switch v-model="form.use_web_search" active-text="开启" inactive-text="关闭" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="范围限定">
          <el-input v-model="form.scope_hint" placeholder="可选：教材版本 / 章节限定，如：仅人教版2024新版第1-3章" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="generating" @click="onGenerate">
            {{ generating ? '正在梳理（约 30-90 秒）…' : '开始梳理' }}
          </el-button>
          <el-checkbox v-model="form.fallback_sample" class="sample-check">LLM 不可用时回退内置示例</el-checkbox>
        </el-form-item>
      </el-form>
    </el-card>

    <el-alert
      v-if="errorMsg"
      type="error"
      :title="errorMsg"
      show-icon
      :closable="true"
      class="error-alert"
    />

    <template v-if="outline">
      <el-card shadow="never" class="result-card">
        <template #header>
          <div class="card-header">
            <span class="title">📘 {{ outline.course }} — 学习内容与要求梳理</span>
            <div class="actions">
              <el-tag size="small" type="info">{{ outline.subject_name }}</el-tag>
              <el-tag v-if="outline.grade_level" size="small" type="info">{{ outline.grade_level }}</el-tag>
              <el-tag size="small" :type="outline.used_web_search ? 'success' : 'warning'">
                {{ outline.used_web_search ? '已联网检索' : (outline.is_sample ? '离线知识包' : '未联网（依据模型知识）') }}
              </el-tag>
              <el-dropdown>
                <el-button type="primary" size="small">
                  导出 <el-icon><arrow-down /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="onExport('docx')">Word 文档 (.docx)</el-dropdown-item>
                    <el-dropdown-item @click="onExport('md')">Markdown (.md)</el-dropdown-item>
                    <el-dropdown-item @click="onExport('json')">JSON 数据 (.json)</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </template>

        <el-alert
          v-if="outline.is_sample"
          type="info"
          show-icon
          :closable="false"
          class="sample-alert"
          title="当前为离线梳理结果"
          :description="`由「${outline.model || '内置知识包'}」生成，未调用大模型：内容框架、要求表述与材料出处均来自内置知识库，可在 backend/.env 配置 API Key 后获得更贴合你输入的梳理。`"
        />

        <el-descriptions v-if="outline.scope" :column="1" border size="small" class="scope-desc">
          <el-descriptions-item label="梳理范围">{{ outline.scope }}</el-descriptions-item>
          <el-descriptions-item v-if="outline.scope_included?.length" label="覆盖范围">
            <el-tag v-for="(s, i) in outline.scope_included" :key="i" size="small" type="success" class="scope-tag">{{ s }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="outline.scope_excluded?.length" label="不覆盖/仅了解">
            <el-tag v-for="(s, i) in outline.scope_excluded" :key="i" size="small" type="info" class="scope-tag">{{ s }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 成果概览：一眼看清规模与完整性 -->
        <div class="overview">
          <div class="overview-item">
            <span class="num">{{ outline.units.length }}</span>
            <span class="label">单元</span>
          </div>
          <div class="overview-item">
            <span class="num">{{ stats.contentCount }}</span>
            <span class="label">学习内容</span>
          </div>
          <div class="overview-item">
            <span class="num">{{ stats.hours }}</span>
            <span class="label">建议课时</span>
          </div>
          <div class="overview-item">
            <span class="num">{{ outline.connections.length }}</span>
            <span class="label">必要联系</span>
          </div>
          <div class="overview-item">
            <span class="num">{{ outline.sources.length }}</span>
            <span class="label">材料出处</span>
          </div>
        </div>

        <!-- 学习内容与要求清单 -->
        <h3 class="section-title">一、学习内容与要求清单</h3>
        <el-collapse v-model="expandedUnits">
          <el-collapse-item v-for="(unit, ui) in outline.units" :key="unit.name" :name="ui">
            <template #title>
              <span class="unit-title">{{ ui + 1 }}. {{ unit.name }}</span>
              <el-tag size="small" type="info" class="unit-tag">{{ unit.contents.length }} 条内容</el-tag>
              <span v-if="unit.textbook_ref" class="unit-ref">{{ unit.textbook_ref }}</span>
            </template>
            <p v-if="unit.description" class="unit-desc">{{ unit.description }}</p>
            <el-table :data="unit.contents" border size="small">
              <el-table-column type="index" label="#" width="45" />
              <el-table-column prop="topic" label="学习内容" width="170" />
              <el-table-column prop="description" label="内容说明" min-width="160" show-overflow-tooltip />
              <el-table-column prop="requirement" label="课标要求" min-width="240" />
              <el-table-column label="要求水平" width="90">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.requirement_level }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="认知水平" width="90">
                <template #default="{ row }">
                  {{ COGNITIVE_LEVEL_MAP[row.cognitive_level] || row.cognitive_level }}
                </template>
              </el-table-column>
              <el-table-column label="课时" width="70">
                <template #default="{ row }">
                  {{ row.suggested_hours ?? '-' }}
                </template>
              </el-table-column>
            </el-table>
          </el-collapse-item>
        </el-collapse>

        <!-- 必要联系 -->
        <h3 class="section-title">二、必要联系</h3>
        <el-table :data="outline.connections" border size="small">
          <el-table-column prop="from_topic" label="起始内容" width="180" />
          <el-table-column prop="to_topic" label="指向内容" width="180" />
          <el-table-column label="联系类型" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="LINK_TYPE_MAP[row.link_type]?.type || 'info'">
                {{ LINK_TYPE_MAP[row.link_type]?.label || row.link_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="300" />
        </el-table>

        <!-- 材料出处 -->
        <h3 class="section-title">三、材料出处</h3>
        <ol class="source-list">
          <li v-for="(s, si) in outline.sources" :key="si">
            <b>{{ s.title }}</b>
            <el-tag size="small" type="info" class="source-tag">{{ SOURCE_TYPE_MAP[s.source_type] || s.source_type }}</el-tag>
            <span v-if="s.publisher" class="publisher">（{{ s.publisher }}）</span>
            <div v-if="s.url" class="source-url">
              链接：<a :href="s.url" target="_blank" rel="noopener">{{ s.url }}</a>
            </div>
            <div v-if="s.usage" class="source-usage">用途：{{ s.usage }}</div>
          </li>
        </ol>
      </el-card>
    </template>

    <!-- 历史记录 -->
    <el-card v-if="history.length > 0" shadow="never" class="history-card">
      <template #header><span class="title">🗂 我的梳理记录</span></template>
      <el-table :data="history" size="small" @row-click="onLoadHistory">
        <el-table-column prop="course_query" label="课程" min-width="200" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
              {{ row.status === 'completed' ? '完成' : row.status === 'failed' ? '失败' : '进行中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 导入课表 / 课程大纲 -->
    <FileImportDialog
      v-model="showImport"
      title="导入课表 / 课程大纲"
      :steps="IMPORT_STEPS"
      :field-rows="IMPORT_FIELDS"
      accept=".csv,.xlsx,.txt,.md,.json"
      tip="支持 .csv / .xlsx（按模板列）、.txt / .md（章节+条目文本）、.json（本系统导出文件），单文件不超过 5MB"
      accept-text="csv / xlsx / txt / md / json"
      template-name="课表大纲导入模板.csv"
      :download-template="downloadImportTemplate"
      :submit="doImport"
      @imported="onImported"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowDown, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import FileImportDialog from '@/components/common/FileImportDialog.vue'
import type { ImportDialogResult, ImportFieldRow } from '@/components/common/importTypes'
import {
  COGNITIVE_LEVEL_MAP,
  LINK_TYPE_MAP,
  SOURCE_TYPE_MAP,
  downloadExport,
  downloadImportTemplate,
  generateOutline,
  getOutline,
  importOutlineFile,
  listOutlines,
  type CurriculumOutlineData,
  type CurriculumOutlineRecord,
} from '@/services/curriculum'

const showImport = ref(false)

const IMPORT_STEPS = [
  '下载模板，按表头填写单元与学习内容；也可直接上传 .txt / .md 章节文本，或用本系统导出的 .json',
  '上传文件，系统按模板列解析单元、学习内容、要求与课时',
  '导入后直接生成一条可用的梳理记录，「材料出处」会如实标注为上传文件',
]

const IMPORT_FIELDS: ImportFieldRow[] = [
  { field: '课程名称', required: '是', desc: '如「数据结构」；也识别 课程 / course' },
  { field: '学科', required: '否', desc: '数学 / 物理学 / 化学 / 计算机科学 等，留空按课程名推断' },
  { field: '学段年级', required: '否', desc: '如「大二」「七年级」「高一」' },
  { field: '单元', required: '否', desc: '如「线性表」；留空归入「未分单元」' },
  { field: '学习内容', required: '是', desc: '该单元下的一条学习内容主题' },
  { field: '内容说明', required: '否', desc: '对这条内容的简要说明' },
  { field: '要求', required: '否', desc: '课标要求表述，如「掌握线性表的抽象数据类型定义」' },
  { field: '要求水平', required: '否', desc: '了解 / 理解 / 掌握 / 运用' },
  { field: '认知水平', required: '否', desc: 'remember / understand / apply / analyze / evaluate / create' },
  { field: '建议课时', required: '否', desc: '数字，如 2' },
  { field: '教材出处', required: '否', desc: '如「严蔚敏《数据结构》第2章」' },
]

const SUBJECTS = [
  { id: 'math', name: '数学' },
  { id: 'physics', name: '物理学' },
  { id: 'chemistry', name: '化学' },
  { id: 'biology', name: '生物学' },
  { id: 'cs', name: '计算机科学' },
  { id: 'chinese', name: '语文' },
  { id: 'english', name: '英语' },
  { id: 'history', name: '历史' },
  { id: 'geography', name: '地理' },
  { id: 'politics', name: '政治' },
]

const form = ref({
  course_query: '',
  grade_level: '',
  subject: '',
  scope_hint: '',
  use_web_search: true,
  fallback_sample: false,
})

// 内置知识包覆盖的课程（无大模型 Key 时也能完整演示）
const QUICK_PICKS = [
  { label: '数据结构·二叉树', course: '数据结构', grade: '大二', hint: '二叉树' },
  { label: '高等数学', course: '高等数学', grade: '大一', hint: '' },
  { label: '线性代数', course: '线性代数', grade: '大二', hint: '' },
  { label: '大学物理', course: '大学物理', grade: '大二', hint: '' },
  { label: '初中数学七上', course: '初中数学七年级上册', grade: '七年级', hint: '' },
  { label: '高中数学', course: '高中数学', grade: '高一', hint: '' },
  { label: '高中物理', course: '高中物理', grade: '高一', hint: '' },
  { label: '高中化学', course: '高中化学', grade: '高一', hint: '' },
]

function fillQuick(p: { course: string; grade: string; hint: string }) {
  form.value.course_query = p.course
  form.value.grade_level = p.grade
  form.value.scope_hint = p.hint
}

const generating = ref(false)
const errorMsg = ref('')
const record = ref<CurriculumOutlineRecord | null>(null)
const outline = ref<CurriculumOutlineData | null>(null)
const expandedUnits = ref<number[]>([0])
const history = ref<CurriculumOutlineRecord[]>([])

// 成果概览统计
const stats = computed(() => {
  const units = outline.value?.units || []
  const contentCount = units.reduce((sum, u) => sum + (u.contents?.length || 0), 0)
  const hours = units.reduce(
    (sum, u) => sum + (u.contents || []).reduce((s, c) => s + (c.suggested_hours || 0), 0),
    0,
  )
  return { contentCount, hours: Math.round(hours) }
})

async function onGenerate() {
  if (!form.value.course_query.trim()) {
    ElMessage.warning('请先输入想学的课程')
    return
  }
  generating.value = true
  errorMsg.value = ''
  outline.value = null
  try {
    const res = await generateOutline({
      course_query: form.value.course_query.trim(),
      grade_level: form.value.grade_level.trim() || undefined,
      subject: form.value.subject || undefined,
      scope_hint: form.value.scope_hint.trim() || undefined,
      use_web_search: form.value.use_web_search,
      fallback_sample: form.value.fallback_sample,
    })
    record.value = res
    if (res.outline) {
      outline.value = res.outline
      expandedUnits.value = res.outline.units.map((_, i) => i)
    } else {
      errorMsg.value = res.error_message || '生成失败'
    }
  } catch (e: any) {
    // 优先使用后端返回的具体原因（AppException 的 message），而不是 axios 的英文提示
    errorMsg.value =
      e?.response?.data?.message ||
      e?.message ||
      '生成失败，请稍后重试'
  } finally {
    generating.value = false
    loadHistory()
  }
}

async function loadHistory() {
  try {
    const res = await listOutlines(1, 10)
    history.value = res.items
  } catch {
    /* 历史列表加载失败不阻塞主流程 */
  }
}

async function onLoadHistory(row: CurriculumOutlineRecord) {
  try {
    const res = await getOutline(row.id)
    if (res.outline) {
      record.value = res
      outline.value = res.outline
      expandedUnits.value = res.outline.units.map((_, i) => i)
    } else {
      ElMessage.info('该记录暂无大纲内容')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  }
}

async function onExport(format: 'json' | 'md' | 'docx') {
  if (!record.value) return
  try {
    const course = outline.value?.course || record.value.course_query
    const ext = format === 'docx' ? 'docx' : format
    await downloadExport(record.value.id, format, `课程梳理_${course}.${ext}`)
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  }
}

/** 导入文件：解析结果整理成对话框摘要 */
async function doImport(file: File): Promise<ImportDialogResult> {
  const res = await importOutlineFile(file)
  const data = res.outline
  if (!data) {
    return {
      title: res.error_message || '文件解析失败，未生成梳理结果',
      tone: 'error',
      payload: res,
    }
  }
  const units = data.units?.length ?? 0
  const contents = (data.units || []).reduce((sum, u) => sum + (u.contents?.length || 0), 0)
  return {
    title: `已生成《${data.course || res.course_query}》的梳理结果`,
    tone: 'success',
    summary: [
      { text: `${units} 个单元`, tone: 'ok' },
      { text: `${contents} 条学习内容`, tone: 'ok' },
      { text: `${data.connections?.length ?? 0} 条必要联系`, tone: 'muted' },
      { text: `已保存到「我的梳理记录」`, tone: 'muted' },
    ],
    payload: res,
  }
}

/** 导入成功后直接展示这条梳理结果 */
async function onImported(result: ImportDialogResult): Promise<void> {
  const res = result.payload as CurriculumOutlineRecord | undefined
  if (!res?.outline) return
  record.value = res
  outline.value = res.outline
  expandedUnits.value = res.outline.units.map((_, i) => i)
  if (res.course_query) form.value.course_query = res.course_query
  await loadHistory()
}

onMounted(loadHistory)
</script>

<style scoped>
.curriculum-page {
  padding: 20px;
  max-width: 1100px;
  margin: 0 auto;
}
.input-card,
.result-card,
.history-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-header .title {
  font-weight: 600;
}
.course-input {
  width: 100%;
}
.quick-picks {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}
.quick-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.quick-tag {
  cursor: pointer;
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sample-check {
  margin-left: 16px;
}
.error-alert {
  margin-bottom: 20px;
}
.section-title {
  margin: 24px 0 12px;
  font-size: 16px;
}
.unit-title {
  font-weight: 600;
}
.unit-tag {
  margin-left: 8px;
}
.unit-ref {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.unit-desc {
  color: var(--el-text-color-secondary);
  margin: 0 0 10px;
}
.scope-desc {
  margin-bottom: 8px;
}
.sample-alert {
  margin: 12px 0;
}
.scope-tag {
  margin: 3px 6px 3px 0;
}
.overview {
  display: flex;
  gap: 12px;
  margin: 16px 0 4px;
}
.overview-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 6px;
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}
.overview-item .num {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-color-primary);
  line-height: 1.2;
}
.overview-item .label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.source-list {
  padding-left: 20px;
  line-height: 1.8;
}
.source-tag {
  margin-left: 8px;
}
.publisher {
  color: var(--el-text-color-secondary);
}
.source-url,
.source-usage {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.source-url a {
  color: var(--el-color-primary);
}
</style>
