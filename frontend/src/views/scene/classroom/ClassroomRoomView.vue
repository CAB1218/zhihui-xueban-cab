<template>
  <div class="classroom-room">
    <!-- ============ 课堂大厅 ============ -->
    <template v-if="!current">
      <el-card shadow="never" class="lobby-card">
        <template #header>
          <div class="card-header">
            <span class="title">🎓 课堂互动</span>
            <el-tag size="small" type="info">进入课堂后可举手、投票、查看参与者</el-tag>
          </div>
        </template>

        <el-row :gutter="16">
          <el-col :xs="24" :md="12">
            <div class="panel">
              <div class="panel__title">发起课堂（教师）</div>
              <el-form v-if="isTeacher" label-width="80px" @submit.prevent="onCreate">
                <el-form-item label="课堂主题">
                  <el-input v-model="createForm.title" placeholder="如：一元二次方程 第2课时" clearable />
                </el-form-item>
                <el-form-item label="所属课程">
                  <el-select
                    ref="courseSelectRef"
                    v-model="createForm.course_id"
                    placeholder="选择课程"
                    style="width: 100%"
                    filterable
                    :loading="courseLoading"
                  >
                    <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id">
                      <span class="course-option__name">{{ c.name }}</span>
                      <span v-if="c.grade" class="course-option__meta">{{ c.grade }}</span>
                    </el-option>
                    <template #empty>
                      <div class="course-empty">暂无课程，用下方按钮新建或导入</div>
                    </template>
                    <template #footer>
                      <div class="course-select__footer">
                        <el-button link type="primary" :icon="Plus" @click="openCreateCourse">新建课程</el-button>
                        <el-button link type="primary" :icon="Upload" @click="openCourseImport">导入课程</el-button>
                      </div>
                    </template>
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="creating" @click="onCreate">创建并进入课堂</el-button>
                </el-form-item>
              </el-form>
              <div v-else class="role-hint">
                当前是学生账号，发起课堂需要教师身份。请用右侧「加入码」进入老师已开的课堂。
              </div>
            </div>
          </el-col>
          <el-col :xs="24" :md="12">
            <div class="panel">
              <div class="panel__title">加入课堂（学生）</div>
              <el-form label-width="80px" @submit.prevent="onJoinByCode">
                <el-form-item label="加入码">
                  <el-input v-model="joinCode" placeholder="输入 6 位加入码" maxlength="6" clearable />
                </el-form-item>
                <el-form-item>
                  <el-button type="success" :loading="joining" @click="onJoinByCode">加入课堂</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-col>
        </el-row>

        <el-divider content-position="left">我的课堂</el-divider>

        <el-table v-loading="loading" :data="classrooms" size="small" empty-text="暂无课堂，先创建一节">
          <el-table-column prop="title" label="课堂主题" min-width="180" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="participant_count" label="人数" width="80" />
          <el-table-column prop="access_code" label="加入码" width="100" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="enterRoom(row)">进入</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- ============ 新建课程（教师建课堂时临时建） ============ -->
      <el-dialog v-model="createCourseVisible" title="新建课程" width="440px">
        <el-form label-width="72px" @submit.prevent>
          <el-form-item label="课程名称" required>
            <el-input
              v-model="createCourseForm.name"
              placeholder="如：操作系统"
              maxlength="100"
              clearable
              @keyup.enter="doCreateCourse"
            />
          </el-form-item>
          <el-form-item label="学科">
            <el-input v-model="createCourseForm.subject" placeholder="选填，可写 计算机科学 / 数学，留空自动推断" />
          </el-form-item>
          <el-form-item label="年级">
            <el-input v-model="createCourseForm.grade" placeholder="选填，如 大三 / 2024级" />
          </el-form-item>
        </el-form>
        <div class="dialog-tip">建好后会自动选中该课程；同名课程已存在时直接选中已有课程。</div>
        <template #footer>
          <el-button @click="createCourseVisible = false">取消</el-button>
          <el-button type="primary" :loading="creatingCourse" @click="doCreateCourse">创建并选中</el-button>
        </template>
      </el-dialog>

      <!-- ============ 导入课程 ============ -->
      <FileImportDialog
        v-model="courseImportVisible"
        title="导入课程"
        :steps="COURSE_IMPORT_STEPS"
        :field-rows="COURSE_IMPORT_FIELDS"
        accept=".csv,.xlsx"
        accept-text="csv / xlsx"
        tip="支持 .csv / .xlsx，单文件不超过 5MB；同名课程会跳过，不会覆盖已有课程"
        template-name="课程导入模板.csv"
        :download-template="learningAdviceApi.downloadCourseTemplate"
        :submit="doImportCourses"
        @imported="onCoursesImported"
      />
    </template>

    <!-- ============ 课堂房间 ============ -->
    <template v-else>
      <el-card shadow="never" class="room-card">
        <template #header>
          <div class="card-header">
            <div class="room-head">
              <span class="title">{{ current.title }}</span>
              <el-tag :type="statusType(current.status)" size="small">{{ statusText(current.status) }}</el-tag>
              <el-tag v-if="current.access_code" size="small" type="info">加入码 {{ current.access_code }}</el-tag>
            </div>
            <div>
              <el-button size="small" @click="exitRoom">返回大厅</el-button>
            </div>
          </div>
        </template>

        <el-row :gutter="16">
          <!-- 参与者 -->
          <el-col :xs="24" :md="9">
            <div class="panel">
              <div class="panel__title">
                参与者（{{ participants.length }}）
                <el-tag v-if="raisedCount" type="warning" size="small">举手 {{ raisedCount }}</el-tag>
              </div>
              <div v-if="!participants.length" class="empty">暂无参与者</div>
              <div v-for="p in participants" :key="p.user_id" class="participant">
                <span class="participant__name">
                  {{ p.name }}
                  <el-tag v-if="p.role === 'teacher'" size="small" type="success">教师</el-tag>
                </span>
                <el-tag v-if="p.hand_raised" type="warning" size="small">已举手</el-tag>
              </div>
              <div class="actions">
                <el-button :type="myRaised ? 'warning' : 'primary'" plain @click="toggleHand">
                  {{ myRaised ? '放下手' : '举手提问' }}
                </el-button>
                <el-button v-if="isTeacher" type="danger" plain @click="onEnd">结束课堂</el-button>
              </div>
            </div>
          </el-col>

          <!-- 投票 -->
          <el-col :xs="24" :md="15">
            <div class="panel">
              <div class="panel__title">
                课堂投票
                <el-button v-if="isTeacher" size="small" type="primary" plain @click="pollDialog = true">
                  发起投票
                </el-button>
              </div>

              <div v-if="!polls.length" class="empty">还没有投票</div>

              <div v-for="poll in polls" :key="poll.id" class="poll">
                <div class="poll__q">
                  {{ poll.question }}
                  <el-tag :type="poll.status === 'active' ? 'success' : 'info'" size="small">
                    {{ poll.status === 'active' ? '进行中' : '已结束' }}
                  </el-tag>
                  <span class="poll__count">{{ poll.total_votes }} 票</span>
                </div>
                <div class="poll__options">
                  <el-radio-group v-model="voteChoice[poll.id]" :disabled="poll.status !== 'active'">
                    <el-radio v-for="(opt, idx) in poll.options" :key="idx" :value="idx">{{ opt }}</el-radio>
                  </el-radio-group>
                </div>
                <div class="poll__footer">
                  <el-button
                    size="small"
                    type="primary"
                    :disabled="poll.status !== 'active'"
                    @click="onVote(poll)"
                  >
                    投票
                  </el-button>
                  <el-button size="small" link @click="loadResult(poll)">查看结果</el-button>
                </div>
                <div v-if="results[poll.id]" class="poll__result">
                  <div v-for="r in results[poll.id]" :key="r.index" class="result-row">
                    <span class="result-row__label">{{ r.text }}</span>
                    <el-progress :percentage="Number(r.percentage)" :stroke-width="12" style="flex: 1" />
                    <span class="result-row__num">{{ r.count }} 票</span>
                  </div>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <el-dialog v-model="pollDialog" title="发起投票" width="480px">
        <el-form label-width="70px">
          <el-form-item label="问题">
            <el-input v-model="pollForm.question" placeholder="如：这道题的正确选项是？" />
          </el-form-item>
          <el-form-item label="选项">
            <el-input
              v-model="pollForm.optionsText"
              type="textarea"
              :rows="4"
              placeholder="每行一个选项，如：&#10;A. 1&#10;B. 2&#10;C. 3"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="pollDialog = false">取消</el-button>
          <el-button type="primary" :loading="pollCreating" @click="onCreatePoll">发起</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * 课堂互动页面
 * 大厅（我的课堂 / 创建 / 加入码加入）+ 房间（参与者、举手、投票、结束）
 * 后端已提供对应接口，实时性用 3 秒轮询实现（无需 WebSocket 也能用）
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'
import FileImportDialog from '@/components/common/FileImportDialog.vue'
import type { ImportDialogResult, ImportFieldRow, ImportSummaryPart } from '@/components/common/importTypes'
import {
  learningAdviceApi,
  type AdviceCourse,
  type CourseImportResult,
} from '@/services/learningAdvice'
import { useAuthStore } from '@/stores/auth'
import {
  classroomApi,
  type ClassroomInfo,
  type ClassroomParticipantInfo,
  type PollItem,
  type PollResult,
} from '@/services/classroom'

const loading = ref(false)
const creating = ref(false)
const joining = ref(false)
const pollCreating = ref(false)
const pollDialog = ref(false)

const classrooms = ref<ClassroomInfo[]>([])
const courses = ref<AdviceCourse[]>([])
const courseLoading = ref(false)
const courseSelectRef = ref<{ blur: () => void }>()
const current = ref<ClassroomInfo | null>(null)
const participants = ref<ClassroomParticipantInfo[]>([])
const polls = ref<PollItem[]>([])
const voteChoice = reactive<Record<string | number, number>>({})
const results = reactive<Record<string | number, PollResult['results']>>({})

const createForm = reactive<{ title: string; course_id?: number }>({ title: '' })
const joinCode = ref('')
const pollForm = reactive({ question: '', optionsText: '' })

/** 新建 / 导入课程 */
const createCourseVisible = ref(false)
const creatingCourse = ref(false)
const createCourseForm = reactive({ name: '', subject: '', grade: '' })
const courseImportVisible = ref(false)

const COURSE_IMPORT_STEPS = [
  '下载模板，至少填写「课程名称」一列；学科、年级、学期、编码、描述都可留空',
  '上传 .csv / .xlsx，系统逐行校验课程名称与长度，同名校验在库里比对',
  '导入成功后课程出现在「所属课程」下拉里，选中即可发起课堂',
]

const COURSE_IMPORT_FIELDS: ImportFieldRow[] = [
  { field: '课程名称', required: '是', desc: '如「操作系统」，与已有课程同名会跳过，不会覆盖' },
  { field: '学科', required: '否', desc: '可写「计算机科学 / 数学 / 物理」，也可直接写 cs / math；留空按课程名猜' },
  { field: '年级', required: '否', desc: '如「大二」「2024级」，留空记为「未设置」' },
  { field: '学期', required: '否', desc: '如 2026-fall，留空按当前时间推断' },
  { field: '课程编码', required: '否', desc: '如 CS301；与已有课程编码重复会跳过' },
  { field: '课程描述', required: '否', desc: '一句话说明课程内容，便于在大纲/建议里对照' },
]

/** 当前登录用户 */
const authStore = useAuthStore()

const meId = computed<number | undefined>(() => authStore.user?.id)
const isTeacher = computed(() => authStore.isTeacher)

const myRaised = computed(() => {
  const mine = participants.value.find((p) => p.user_id === meId.value)
  return Boolean(mine?.hand_raised)
})

const raisedCount = computed(() => participants.value.filter((p) => p.hand_raised).length)

function statusText(status?: string): string {
  if (status === 'active') return '进行中'
  if (status === 'ended') return '已结束'
  return '未开始'
}

function statusType(status?: string): 'success' | 'info' | 'warning' {
  if (status === 'active') return 'success'
  if (status === 'ended') return 'info'
  return 'warning'
}

async function loadCourses() {
  if (!isTeacher.value) {
    courses.value = []
    return
  }
  courseLoading.value = true
  try {
    // 用 /learning-advice/courses（返回租户内全部课程）而不是 /teachers/courses：
    // 后者只返回「本人创建」的课程，新教师/接管别人课程的教师会看到「无数据」无法建课堂。
    const list = await learningAdviceApi.courses()
    courses.value = list
    if (!createForm.course_id && list.length) createForm.course_id = list[0].id
    if (createForm.course_id && !list.some((c) => c.id === createForm.course_id)) {
      createForm.course_id = list[0]?.id
    }
  } catch (e) {
    console.error('加载课程失败:', e)
  } finally {
    courseLoading.value = false
  }
}

function openCreateCourse(): void {
  courseSelectRef.value?.blur()
  createCourseForm.name = ''
  createCourseForm.subject = ''
  createCourseForm.grade = ''
  createCourseVisible.value = true
}

async function doCreateCourse(): Promise<void> {
  if (!createCourseForm.name.trim()) {
    ElMessage.warning('请填写课程名称')
    return
  }
  creatingCourse.value = true
  try {
    const created = await learningAdviceApi.createCourse({
      name: createCourseForm.name.trim(),
      subject: createCourseForm.subject.trim() || undefined,
      grade: createCourseForm.grade.trim() || undefined,
    })
    ElMessage.success(created.existed ? '同名课程已存在，已为你选中' : `课程「${created.name}」已创建`)
    createCourseVisible.value = false
    await loadCourses()
    createForm.course_id = created.id
  } catch (e) {
    console.error('创建课程失败:', e)
  } finally {
    creatingCourse.value = false
  }
}

function openCourseImport(): void {
  courseSelectRef.value?.blur()
  courseImportVisible.value = true
}

async function doImportCourses(file: File): Promise<ImportDialogResult> {
  const res: CourseImportResult = await learningAdviceApi.importCourses(file)
  const summary: ImportSummaryPart[] = [
    { text: `文件共 ${res.total} 行`, tone: 'muted' },
    { text: `新增 ${res.created} 门课程`, tone: res.created ? 'ok' : 'bad' },
  ]
  if (res.skipped) summary.push({ text: `同名校验跳过 ${res.skipped} 门`, tone: 'warn' })
  if (res.failed) summary.push({ text: `未通过校验 ${res.failed} 行`, tone: 'bad' })

  let title: string
  let tone: ImportDialogResult['tone']
  if (!res.created && !res.skipped) {
    title = '没有导入任何课程，请按下方原因修正后重试'
    tone = 'error'
  } else if (res.failed) {
    title = `新增 ${res.created} 门课程，${res.failed} 行未通过校验`
    tone = 'warning'
  } else if (!res.created && res.skipped) {
    title = `没有新增课程：${res.skipped} 门已存在`
    tone = 'warning'
  } else {
    title = `成功新增 ${res.created} 门课程`
    tone = 'success'
  }

  return { title, tone, summary, errors: res.errors, errorsTruncated: res.errors_truncated, payload: res }
}

async function onCoursesImported(result: ImportDialogResult): Promise<void> {
  const payload = result.payload as CourseImportResult | undefined
  await loadCourses()
  const first = payload?.created_rows?.[0]?.name
  const hit = first ? courses.value.find((c) => c.name === first) : undefined
  if (hit) createForm.course_id = hit.id
}

async function loadLobby() {
  loading.value = true
  try {
    const [list] = await Promise.all([classroomApi.listClassrooms(), loadCourses()])
    classrooms.value = list
  } catch (e) {
    console.error('加载课堂列表失败:', e)
  } finally {
    loading.value = false
  }
}

async function enterRoom(classroom: ClassroomInfo) {
  current.value = classroom
  await refreshRoom()
  startPolling()
}

async function refreshRoom() {
  if (!current.value) return
  try {
    const [ps, pl, detail] = await Promise.all([
      classroomApi.getParticipants(current.value.id),
      classroomApi.listPolls(current.value.id),
      classroomApi.getClassroom(current.value.id as string),
    ])
    participants.value = ps
    polls.value = pl
    current.value = detail
    if (detail.status === 'ended') stopPolling()
  } catch (e) {
    console.error('刷新课堂失败:', e)
  }
}

async function onCreate() {
  if (!createForm.title.trim()) {
    ElMessage.warning('请填写课堂主题')
    return
  }
  if (!createForm.course_id) {
    ElMessage.warning('请先在「所属课程」里选择课程；没有课程可点下拉底部的「新建课程」')
    return
  }
  creating.value = true
  try {
    const created = await classroomApi.createClassroom({
      title: createForm.title.trim(),
      course_id: createForm.course_id,
    })
    ElMessage.success('课堂已创建')
    createForm.title = ''
    await enterRoom(created)
  } catch (e) {
    console.error('创建课堂失败:', e)
  } finally {
    creating.value = false
  }
}

async function onJoinByCode() {
  if (!joinCode.value.trim()) {
    ElMessage.warning('请输入加入码')
    return
  }
  joining.value = true
  try {
    const classroom = await classroomApi.joinByCode(joinCode.value.trim())
    ElMessage.success('已加入课堂')
    joinCode.value = ''
    await enterRoom(classroom)
  } catch (e) {
    console.error('加入课堂失败:', e)
  } finally {
    joining.value = false
  }
}

async function toggleHand() {
  if (!current.value) return
  try {
    await classroomApi.raiseHand(current.value.id)
    await refreshRoom()
  } catch (e) {
    console.error('举手失败:', e)
  }
}

async function onCreatePoll() {
  if (!current.value) return
  const options = pollForm.optionsText
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  if (!pollForm.question.trim() || options.length < 2) {
    ElMessage.warning('请填写问题并至少两个选项')
    return
  }
  pollCreating.value = true
  try {
    await classroomApi.createPoll(current.value.id, {
      question: pollForm.question.trim(),
      options,
    })
    ElMessage.success('投票已发起')
    pollForm.question = ''
    pollForm.optionsText = ''
    pollDialog.value = false
    await refreshRoom()
  } catch (e) {
    console.error('发起投票失败:', e)
  } finally {
    pollCreating.value = false
  }
}

async function onVote(poll: PollItem) {
  if (!current.value) return
  const choice = voteChoice[poll.id]
  if (choice === undefined) {
    ElMessage.warning('请先选择一个选项')
    return
  }
  try {
    await classroomApi.votePoll(current.value.id, poll.id, { selected_options: [choice] })
    ElMessage.success('投票成功')
    await loadResult(poll)
    await refreshRoom()
  } catch (e) {
    console.error('投票失败:', e)
  }
}

async function loadResult(poll: PollItem) {
  if (!current.value) return
  try {
    const res = await classroomApi.getPollResult(current.value.id, poll.id)
    results[poll.id] = res.results
  } catch (e) {
    console.error('获取投票结果失败:', e)
  }
}

async function onEnd() {
  if (!current.value) return
  try {
    await ElMessageBox.confirm('确定结束这节课堂吗？结束后无法再投票。', '结束课堂', { type: 'warning' })
  } catch {
    return
  }
  try {
    await classroomApi.endClassroom(current.value.id)
    ElMessage.success('课堂已结束')
    await refreshRoom()
    stopPolling()
  } catch (e) {
    console.error('结束课堂失败:', e)
  }
}

function exitRoom() {
  stopPolling()
  current.value = null
  participants.value = []
  polls.value = []
  loadLobby()
}

let timer: ReturnType<typeof setInterval> | null = null

function startPolling() {
  stopPolling()
  timer = setInterval(refreshRoom, 3000)
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(loadLobby)
onBeforeUnmount(stopPolling)
</script>

<style lang="scss" scoped>
.classroom-room {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  .title {
    font-size: 16px;
    font-weight: 600;
  }
}

.room-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 16px;

  &__title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    margin-bottom: 12px;
  }
}

.empty {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  padding: 8px 0;
}

.role-hint {
  margin-left: 80px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--el-color-info-light-9);
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.6;
}

.course-option__name {
  margin-right: 8px;
}

.course-option__meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.course-select__footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  border-top: 1px solid var(--el-border-color-lighter);
  padding: 6px 12px;

  :deep(.el-button) {
    font-size: 12px;
  }
}

.course-empty {
  padding: 10px 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.dialog-tip {
  margin: 0 0 4px 72px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.participant {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);

  &__name {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
}

.actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.poll {
  border-bottom: 1px dashed var(--el-border-color-lighter);
  padding-bottom: 12px;
  margin-bottom: 12px;

  &__q {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  &__count {
    color: var(--el-text-color-secondary);
    font-weight: 400;
    font-size: 12px;
  }

  &__options {
    margin-bottom: 8px;
  }

  &__footer {
    display: flex;
    gap: 8px;
  }

  &__result {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
}

.result-row {
  display: flex;
  align-items: center;
  gap: 10px;

  &__label {
    width: 90px;
    font-size: 13px;
  }

  &__num {
    width: 56px;
    text-align: right;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}
</style>
