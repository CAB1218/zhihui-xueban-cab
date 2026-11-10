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
              <el-form label-width="80px" @submit.prevent="onCreate">
                <el-form-item label="课堂主题">
                  <el-input v-model="createForm.title" placeholder="如：一元二次方程 第2课时" clearable />
                </el-form-item>
                <el-form-item label="所属课程">
                  <el-select v-model="createForm.course_id" placeholder="选择课程" style="width: 100%">
                    <el-option v-for="c in courses" :key="c.id" :label="c.name" :value="c.id" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="creating" @click="onCreate">创建并进入课堂</el-button>
                </el-form-item>
              </el-form>
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
import api from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import {
  classroomApi,
  type ClassroomInfo,
  type ClassroomParticipantInfo,
  type PollItem,
  type PollResult,
} from '@/services/classroom'

interface CourseOption {
  id: number
  name: string
}

const loading = ref(false)
const creating = ref(false)
const joining = ref(false)
const pollCreating = ref(false)
const pollDialog = ref(false)

const classrooms = ref<ClassroomInfo[]>([])
const courses = ref<CourseOption[]>([])
const current = ref<ClassroomInfo | null>(null)
const participants = ref<ClassroomParticipantInfo[]>([])
const polls = ref<PollItem[]>([])
const voteChoice = reactive<Record<string | number, number>>({})
const results = reactive<Record<string | number, PollResult['results']>>({})

const createForm = reactive<{ title: string; course_id?: number }>({ title: '' })
const joinCode = ref('')
const pollForm = reactive({ question: '', optionsText: '' })

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

async function loadLobby() {
  loading.value = true
  try {
    const [list, courseList] = await Promise.all([
      classroomApi.listClassrooms(),
      api.get('/teachers/courses').then((res: any) => (res.data ?? []) as CourseOption[]).catch(() => []),
    ])
    classrooms.value = list
    courses.value = courseList
    if (!createForm.course_id && courseList.length) createForm.course_id = courseList[0].id
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
