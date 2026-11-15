/**
 * 智慧学伴 用户 Store
 * 管理用户偏好、Onboarding 状态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface UserPreferences {
  /** 主题：light / dark / auto */
  theme: 'light' | 'dark' | 'auto'
  /** 语言 */
  locale: 'zh-CN' | 'en-US'
  /** 默认场景 */
  defaultScene: string
  /** 侧边栏折叠状态 */
  sidebarCollapsed: boolean
  /** 字体大小 */
  fontSize: 'small' | 'medium' | 'large'
  /** 是否显示学伴 */
  showBuddy: boolean
  /** 通知设置 */
  notificationEnabled: boolean
}

export interface OnboardingData {
  role: string
  major: string
  interests: string[]
  goals: string[]
}

const DEFAULT_PREFERENCES: UserPreferences = {
  theme: 'light',
  locale: 'zh-CN',
  defaultScene: 'classroom',
  sidebarCollapsed: false,
  fontSize: 'medium',
  showBuddy: true,
  notificationEnabled: true,
}

export const useUserStore = defineStore('user', () => {
  // ============ State ============

  /** 用户偏好 */
  const preferences = ref<UserPreferences>({
    ...DEFAULT_PREFERENCES,
    ...JSON.parse(localStorage.getItem('user_preferences') || '{}'),
  })

  /** Onboarding 步骤 */
  const onboardingStep = ref<number>(0)

  /** Onboarding 是否完成 */
  const onboardingCompleted = ref<boolean>(
    localStorage.getItem('onboarding_completed') === 'true'
  )

  /** Onboarding 收集的数据 */
  const onboardingData = ref<OnboardingData>({
    ...{ role: '', major: '', interests: [], goals: [] },
    ...JSON.parse(localStorage.getItem('onboarding_data') || '{}'),
  })

  // ============ Getters ============

  /** 是否暗色主题 */
  const isDarkTheme = computed<boolean>(() => {
    if (preferences.value.theme === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return preferences.value.theme === 'dark'
  })

  // ============ Actions ============

  /**
   * 更新用户偏好
   * @param updates 要更新的偏好字段
   */
  function updatePreferences(updates: Partial<UserPreferences>): void {
    preferences.value = { ...preferences.value, ...updates }
    localStorage.setItem('user_preferences', JSON.stringify(preferences.value))
  }

  /**
   * 完成 Onboarding
   */
  function completeOnboarding(): void {
    onboardingCompleted.value = true
    localStorage.setItem('onboarding_completed', 'true')
  }

  /**
   * 重置 Onboarding（用于测试）
   */
  function resetOnboarding(): void {
    onboardingCompleted.value = false
    onboardingStep.value = 0
    onboardingData.value = { role: '', major: '', interests: [], goals: [] }
    localStorage.removeItem('onboarding_completed')
    localStorage.removeItem('onboarding_data')
  }

  /**
   * 设置 Onboarding 数据
   * @param data 部分更新
   */
  function setOnboardingData(data: Partial<OnboardingData>): void {
    onboardingData.value = { ...onboardingData.value, ...data }
    localStorage.setItem('onboarding_data', JSON.stringify(onboardingData.value))
  }

  /**
   * 切换侧边栏折叠状态
   */
  function toggleSidebar(): void {
    updatePreferences({ sidebarCollapsed: !preferences.value.sidebarCollapsed })
  }

  /**
   * 切换主题
   */
  function toggleTheme(): void {
    const themes: ('light' | 'dark' | 'auto')[] = ['light', 'dark', 'auto']
    const currentIdx = themes.indexOf(preferences.value.theme)
    const nextTheme = themes[(currentIdx + 1) % themes.length]
    updatePreferences({ theme: nextTheme })
  }

  return {
    // State
    preferences,
    onboardingStep,
    onboardingCompleted,
    onboardingData,
    // Getters
    isDarkTheme,
    // Actions
    updatePreferences,
    completeOnboarding,
    resetOnboarding,
    setOnboardingData,
    toggleSidebar,
    toggleTheme,
  }
})
