<template>
  <div class="register-view">
    <div class="register-view__card">
      <div class="register-view__header">
        <img src="/favicon.svg" alt="智慧学伴" class="register-view__logo" />
        <h1 class="register-view__title">创建账号</h1>
        <p class="register-view__subtitle">开始你的个性化学习之旅</p>
      </div>

      <el-form
        ref="formRef"
        :model="registerForm"
        :rules="registerRules"
        label-position="top"
        size="large"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="昵称" prop="nickname">
          <el-input
            v-model="registerForm.nickname"
            placeholder="请输入昵称"
            prefix-icon="User"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="请输入邮箱"
            prefix-icon="Message"
            autocomplete="email"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码（至少6位）"
            prefix-icon="Lock"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            prefix-icon="Lock"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item label="我是" prop="role">
          <el-radio-group v-model="registerForm.role" class="register-view__role-group">
            <el-radio-button value="student">学生</el-radio-button>
            <el-radio-button value="teacher">教师</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="学校（选填）" prop="school">
          <el-input
            v-model="registerForm.school"
            placeholder="请输入学校名称"
            prefix-icon="School"
          />
        </el-form-item>

        <el-form-item label="年级（选填）" prop="grade">
          <el-select v-model="registerForm.grade" placeholder="请选择年级" clearable class="register-view__grade-select">
            <el-option v-for="g in grades" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="register-view__submit"
            @click="handleRegister"
          >
            注 册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-view__footer">
        <span>已有账号？</span>
        <el-link type="primary" @click="goLogin">立即登录</el-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 注册页
 * 表单验证 + 角色选择
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const grades = [
  '大一', '大二', '大三', '大四',
  '研一', '研二', '研三',
  '博士一年级', '博士二年级', '博士三年级',
]

const registerForm = reactive({
  nickname: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'student',
  school: '',
  grade: '',
})

// 自定义确认密码校验
const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 2, max: 50, message: '昵称长度2-50个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度6-50个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' },
  ],
}

async function handleRegister(): Promise<void> {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await authStore.register({
        email: registerForm.email,
        password: registerForm.password,
        nickname: registerForm.nickname,
        role: registerForm.role,
        school: registerForm.school || undefined,
        grade: registerForm.grade || undefined,
      })
      ElMessage.success('注册成功')
      // 注册后跳转到 Onboarding 引导
      await router.push({ name: 'onboarding-role' })
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '注册失败'
      ElMessage.error(message)
    } finally {
      loading.value = false
    }
  })
}

function goLogin(): void {
  router.push({ name: 'Login' })
}
</script>

<style lang="scss" scoped>
.register-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #388E3C 0%, #1976D2 100%);
  padding: 20px;

  &__card {
    width: 480px;
    max-height: 90vh;
    overflow-y: auto;
    padding: 40px;
    background: white;
    border-radius: var(--border-radius-lg);
    box-shadow: var(--shadow-lg);
  }

  &__header {
    text-align: center;
    margin-bottom: 28px;
  }

  &__logo {
    width: 48px;
    height: 48px;
    margin-bottom: 12px;
  }

  &__title {
    font-size: 24px;
    font-weight: 700;
    color: var(--color-text-primary);
    margin-bottom: 6px;
  }

  &__subtitle {
    font-size: 14px;
    color: var(--color-text-secondary);
  }

  &__role-group {
    width: 100%;

    :deep(.el-radio-button__inner) {
      width: 50%;
    }
  }

  &__grade-select {
    width: 100%;
  }

  &__submit {
    width: 100%;
  }

  &__footer {
    text-align: center;
    font-size: 14px;
    color: var(--color-text-secondary);
  }
}
</style>
