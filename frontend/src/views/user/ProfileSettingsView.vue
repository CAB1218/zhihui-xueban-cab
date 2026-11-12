<template>
  <div class="settings-view">
    <div class="page-header">
      <div class="page-header__left">
        <h2>个人设置</h2>
        <span class="page-header__hint">修改昵称、头像与学籍信息，也可以在这里更新登录密码</span>
      </div>
      <div class="page-header__actions">
        <el-button :icon="Back" @click="goBack">返回</el-button>
      </div>
    </div>

    <el-row :gutter="14">
      <el-col :xs="24" :lg="16">
        <el-card shadow="never" class="card-block">
          <template #header>
            <div class="card-header">
              <span class="title">基本信息</span>
              <span class="sub">带 * 的为必填</span>
            </div>
          </template>

          <div class="profile-top">
            <el-avatar :size="64" :src="form.avatarUrl || undefined" class="profile-avatar">
              {{ (form.nickname || userName).charAt(0) }}
            </el-avatar>
            <div class="profile-top__meta">
              <div class="profile-top__name">{{ form.nickname || '未命名用户' }}</div>
              <div class="profile-top__role">
                <el-tag size="small" effect="plain">{{ roleLabel }}</el-tag>
                <span class="muted">{{ authStore.user?.email }}</span>
              </div>
            </div>
          </div>

          <el-form
            ref="profileFormRef"
            :model="form"
            :rules="profileRules"
            label-width="92px"
            class="profile-form"
            @submit.prevent
          >
            <el-form-item label="昵称" prop="nickname">
              <el-input v-model="form.nickname" maxlength="50" show-word-limit placeholder="2-50 个字符" />
            </el-form-item>
            <el-form-item label="头像链接" prop="avatarUrl">
              <el-input v-model="form.avatarUrl" clearable placeholder="选填，填入图片地址（https://…）" />
            </el-form-item>
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="form.phone" clearable placeholder="选填，用于联系与找回账号" />
            </el-form-item>
            <el-form-item label="年级" prop="grade">
              <el-input v-model="form.grade" clearable placeholder="如「大二」「2024级」" />
            </el-form-item>
            <el-form-item label="学校" prop="school">
              <el-input v-model="form.school" clearable placeholder="如「示例大学」" />
            </el-form-item>
            <el-form-item label="专业" prop="major">
              <el-input v-model="form.major" maxlength="100" clearable placeholder="如「计算机科学与技术」" />
            </el-form-item>
            <el-form-item label="个人简介" prop="bio">
              <el-input
                v-model="form.bio"
                type="textarea"
                :rows="3"
                maxlength="200"
                show-word-limit
                placeholder="一句话介绍自己，会出现在成长档案等页面"
              />
            </el-form-item>
          </el-form>

          <div class="card-actions">
            <el-button @click="resetForm" :disabled="saving">重置</el-button>
            <el-button type="primary" :loading="saving" @click="saveProfile">保存修改</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="card-block">
          <template #header>
            <div class="card-header"><span class="title">账号信息</span></div>
          </template>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="邮箱">
              {{ authStore.user?.email || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="角色">{{ roleLabel }}</el-descriptions-item>
            <el-descriptions-item label="租户">
              {{ authStore.user?.tenant_id ?? '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">
              {{ formatTime(authStore.user?.created_at) }}
            </el-descriptions-item>
          </el-descriptions>
          <p class="card-tip">邮箱由管理员维护；如需更换请联系管理员。</p>
        </el-card>

        <el-card shadow="never" class="card-block">
          <template #header>
            <div class="card-header"><span class="title">修改密码</span></div>
          </template>
          <el-form
            ref="pwdFormRef"
            :model="pwd"
            :rules="pwdRules"
            label-width="104px"
            @submit.prevent
          >
            <el-form-item label="当前密码" prop="oldPassword">
              <el-input v-model="pwd.oldPassword" type="password" show-password autocomplete="current-password" />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input v-model="pwd.newPassword" type="password" show-password autocomplete="new-password" />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirmPassword">
              <el-input v-model="pwd.confirmPassword" type="password" show-password autocomplete="new-password" />
            </el-form-item>
          </el-form>
          <div class="card-actions card-actions--end">
            <el-button type="primary" plain :loading="changingPwd" @click="changePassword">更新密码</el-button>
          </div>
          <p class="card-tip">密码 6-50 位；修改后当前登录状态保持，下次登录用新密码。</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
/**
 * 个人设置
 * 头像菜单「个人设置」落地页：资料编辑 + 密码修改
 * 依赖 PUT /users/{id}、PUT /users/{id}/password
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Back } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { userApi } from '@/services/user'

const router = useRouter()
const authStore = useAuthStore()

const saving = ref(false)
const changingPwd = ref(false)
const profileFormRef = ref<FormInstance>()
const pwdFormRef = ref<FormInstance>()

const form = reactive({
  nickname: '',
  avatarUrl: '',
  phone: '',
  grade: '',
  school: '',
  major: '',
  bio: '',
})

const pwd = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const userName = computed(() => authStore.user?.nickname ?? '用户')

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    student: '学生',
    teacher: '教师',
    admin: '管理员',
    super_admin: '超级管理员',
  }
  return map[authStore.user?.role ?? ''] ?? authStore.user?.role ?? '—'
})

const profileRules: FormRules = {
  nickname: [
    { required: true, message: '请填写昵称', trigger: 'blur' },
    { min: 2, max: 50, message: '昵称长度 2-50 个字符', trigger: 'blur' },
  ],
  avatarUrl: [{ type: 'url', message: '请填写合法的图片地址（含 http/https）', trigger: 'blur' }],
  phone: [
    {
      pattern: /^[0-9+\-\s()]{6,20}$/,
      message: '手机号格式不正确（6-20 位数字，可带 + - 空格）',
      trigger: 'blur',
    },
  ],
}

const pwdRules: FormRules = {
  oldPassword: [{ required: true, message: '请填写当前密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请填写新密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度 6-50 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_r, value, cb) => {
        if (value !== pwd.newPassword) cb(new Error('两次输入的新密码不一致'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

function formatTime(v?: string): string {
  if (!v) return '—'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN')
}

function fillFromUser(info: {
  nickname?: string
  avatar_url?: string | null
  phone?: string | null
  grade?: string | null
  school?: string | null
  major?: string | null
  bio?: string | null
}): void {
  form.nickname = info.nickname ?? ''
  form.avatarUrl = info.avatar_url ?? ''
  form.phone = info.phone ?? ''
  form.grade = info.grade ?? ''
  form.school = info.school ?? ''
  form.major = info.major ?? ''
  form.bio = info.bio ?? ''
}

function resetForm(): void {
  if (authStore.user) fillFromUser(authStore.user)
  profileFormRef.value?.clearValidate()
}

async function loadProfile(): Promise<void> {
  const uid = authStore.user?.id
  if (!uid) return
  fillFromUser(authStore.user!)
  try {
    const detail = await userApi.getProfile(uid)
    fillFromUser(detail)
  } catch {
    // 详情接口失败时保留 authStore 里的信息，不阻塞页面
  }
}

async function saveProfile(): Promise<void> {
  const uid = authStore.user?.id
  if (!uid) {
    ElMessage.warning('登录状态已失效，请重新登录')
    return
  }
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    await userApi.updateProfile(uid, {
      nickname: form.nickname.trim(),
      avatar_url: form.avatarUrl.trim() || null,
      phone: form.phone.trim() || null,
      grade: form.grade.trim() || null,
      school: form.school.trim() || null,
      major: form.major.trim() || null,
      bio: form.bio.trim() || null,
    })
    await authStore.fetchCurrentUser()
    resetForm()
    ElMessage.success('个人资料已保存')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

async function changePassword(): Promise<void> {
  const uid = authStore.user?.id
  if (!uid) return
  const valid = await pwdFormRef.value?.validate().catch(() => false)
  if (!valid) return

  changingPwd.value = true
  try {
    await userApi.changePassword(uid, pwd.oldPassword, pwd.newPassword)
    pwd.oldPassword = ''
    pwd.newPassword = ''
    pwd.confirmPassword = ''
    pwdFormRef.value?.clearValidate()
    ElMessage.success('密码已更新，下次登录请使用新密码')
  } catch (e: any) {
    ElMessage.error(e?.message || '密码修改失败')
  } finally {
    changingPwd.value = false
  }
}

function goBack(): void {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

onMounted(loadProfile)
</script>

<style lang="scss" scoped>
.settings-view {
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
    color: var(--color-text-secondary);
  }

  &__actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

.card-block {
  margin-bottom: 14px;
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;

  .title {
    font-weight: 600;
  }

  .sub {
    font-size: 12px;
    color: var(--color-text-secondary);
  }
}

.profile-top {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--color-border-light);

  &__meta {
    min-width: 0;
  }

  &__name {
    font-size: 16px;
    font-weight: 600;
  }

  &__role {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
    font-size: 12px;
    flex-wrap: wrap;
  }
}

.profile-avatar {
  flex-shrink: 0;
  background: var(--scene-primary-color, #1976d2);
  color: #fff;
  font-size: 24px;
}

.profile-form {
  max-width: 560px;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 6px;

  &--end {
    padding-top: 0;
    margin-top: 4px;
  }
}

.card-tip {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.muted {
  color: var(--color-text-secondary);
}
</style>
