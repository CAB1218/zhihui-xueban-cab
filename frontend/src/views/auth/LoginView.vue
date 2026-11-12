<template>
  <div class="login-view">
    <div class="login-view__card">
      <div class="login-view__header">
        <img src="/favicon.svg" alt="智慧学伴" class="login-view__logo" />
        <h1 class="login-view__title">智慧学伴智能体</h1>
        <p class="login-view__subtitle">AI 驱动的个性化学习体验</p>
      </div>

      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="loginRules"
        label-position="top"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="loginForm.email"
            placeholder="请输入邮箱"
            prefix-icon="Message"
            autocomplete="email"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="login-view__submit"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-view__footer">
        <span>还没有账号？</span>
        <el-link type="primary" @click="goRegister">立即注册</el-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 登录页
 * 表单验证 + 登录后 Onboarding 检查
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

const loginForm = reactive({
  email: '',
  password: '',
})

const loginRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
}

async function handleLogin(): Promise<void> {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await authStore.login(loginForm)
      ElMessage.success('登录成功')

      // 检查 Onboarding 状态
      if (authStore.user && !authStore.user.onboarding_completed) {
        await router.push({ name: 'onboarding-role' })
      } else {
        const redirect = (router.currentRoute.value.query.redirect as string) || '/'
        await router.push(redirect)
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '登录失败'
      ElMessage.error(message)
    } finally {
      loading.value = false
    }
  })
}

function goRegister(): void {
  router.push({ name: 'Register' })
}
</script>

<style lang="scss" scoped>
.login-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1976D2 0%, #7B1FA2 100%);

  &__card {
    width: 420px;
    padding: 40px;
    background: white;
    border-radius: var(--border-radius-lg);
    box-shadow: var(--shadow-lg);
  }

  &__header {
    text-align: center;
    margin-bottom: 32px;
  }

  &__logo {
    width: 48px;
    height: 48px;
    margin-bottom: 16px;
  }

  &__title {
    font-size: 24px;
    font-weight: 700;
    color: var(--color-text-primary);
    margin-bottom: 8px;
  }

  &__subtitle {
    font-size: 14px;
    color: var(--color-text-secondary);
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
