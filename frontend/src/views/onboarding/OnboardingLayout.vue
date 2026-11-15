<template>
  <div class="onboarding-layout">
    <div class="onboarding-layout__container">
      <!-- 顶部进度条 -->
      <div class="onboarding-layout__progress">
        <el-steps :active="currentStep" :max="4" finish-status="success" simple>
          <el-step title="选择角色" />
          <el-step title="所在专业" />
          <el-step title="兴趣课程" />
          <el-step title="学习目标" />
        </el-steps>
      </div>

      <!-- 内容区域 -->
      <div class="onboarding-layout__content">
        <router-view />
      </div>

      <!-- 跳过按钮 -->
      <div class="onboarding-layout__footer">
        <el-button link type="info" @click="handleSkip">跳过引导</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 Onboarding 引导布局
 * 包含进度指示器和跳过按钮
 */
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/services/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const userStore = useUserStore()

const STEP_ROUTES = ['onboarding-role', 'onboarding-major', 'onboarding-interests', 'onboarding-goal']

const currentStep = computed(() => {
  const name = route.name as string
  const idx = STEP_ROUTES.indexOf(name)
  return idx >= 0 ? idx : 0
})

async function handleSkip(): Promise<void> {
  try {
    // ✅ 调用后端接口持久化引导完成状态（跳过时以空数据提交）
    const userId = authStore.user?.id
    if (userId) {
      await authApi.completeOnboarding(userId, {
        role: userStore.onboardingData.role || '',
        major: userStore.onboardingData.major || '',
        interests: userStore.onboardingData.interests || [],
        goals: [],
      })
      await authStore.fetchCurrentUser()
    }
    userStore.completeOnboarding()

    // 确保 authStore 中的 onboarding 状态同步更新
    if (authStore.user) {
      authStore.user.onboarding_completed = true
    }

    // 跳转到默认首页
    const redirect = (route.query.redirect as string) || '/'
    await router.push(redirect)
    ElMessage.info('已跳过引导，可稍后在设置中完善')
  } catch {
    // 即使接口失败也跳转，避免用户卡死
    userStore.completeOnboarding()
    const redirect = (route.query.redirect as string) || '/'
    await router.push(redirect)
    ElMessage.info('已跳过引导，可稍后在设置中完善')
  }
}
</script>

<style lang="scss" scoped>
.onboarding-layout {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

  &__container {
    width: 720px;
    max-width: 90vw;
    padding: 40px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  }

  &__progress {
    margin-bottom: 32px;

    :deep(.el-steps--simple) {
      padding: 12px 24px;
      border-radius: 8px;
    }
  }

  &__content {
    min-height: 300px;
  }

  &__footer {
    margin-top: 24px;
    text-align: center;
  }
}
</style>
