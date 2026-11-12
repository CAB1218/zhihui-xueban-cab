/**
 * AI4Edu 认证 Store
 * 管理JWT Token、用户信息、登录/登出/刷新Token
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/services/auth'
import type { UserInfo, LoginParams, RegisterParams } from '@/services/auth'
import { syncPreferencesFromServer } from '@/utils/preferences'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  // ============ State ============

  /** Access Token */
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  /** Refresh Token */
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  /** 当前用户信息 */
  const user = ref<UserInfo | null>(null)
  /** 加载状态 */
  const loading = ref<boolean>(false)

  // ============ Getters ============

  /** 是否已认证 */
  const isAuthenticated = computed<boolean>(() => !!accessToken.value)

  /** 用户角色 */
  const userRole = computed<string>(() => user.value?.role ?? 'student')

  /** 是否是教师 */
  const isTeacher = computed<boolean>(() =>
    ['teacher', 'admin', 'super_admin'].includes(userRole.value),
  )

  /** 是否是管理员 */
  const isAdmin = computed<boolean>(() => userRole.value === 'admin' || userRole.value === 'super_admin')

  /** 是否需要 Onboarding */
  const needsOnboarding = computed<boolean>(() => {
    return isAuthenticated.value && user.value !== null && !user.value.onboarding_completed
  })

  // ============ Actions ============

  /**
   * 用户登录
   * @param params 登录参数
   */
  async function login(params: LoginParams): Promise<void> {
    loading.value = true
    try {
      const response = await authApi.login(params)
      const { access_token, refresh_token } = response

      // 存储 Token
      accessToken.value = access_token
      refreshToken.value = refresh_token
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      // 获取用户信息
      await fetchCurrentUser()
    } catch (error) {
      clearAuth()
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 用户注册
   * @param params 注册参数
   */
  async function register(params: RegisterParams): Promise<void> {
    loading.value = true
    try {
      const response = await authApi.register(params)
      const { access_token, refresh_token } = response

      accessToken.value = access_token
      refreshToken.value = refresh_token
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      // 获取用户信息
      await fetchCurrentUser()
    } catch (error) {
      clearAuth()
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 刷新 Access Token
   */
  async function refreshAccessToken(): Promise<void> {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }

    try {
      const response = await authApi.refresh(refreshToken.value)
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
    } catch (error) {
      clearAuth()
      throw error
    }
  }

  /**
   * 用户登出
   */
  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      // 即使登出API调用失败，也要清除本地状态
    } finally {
      clearAuth()
      await router.push({ name: 'Login' })
    }
  }

  /**
   * 获取当前用户信息
   */
  async function fetchCurrentUser(): Promise<void> {
    try {
      const userInfo = await authApi.getCurrentUser()
      user.value = userInfo
      // 服务端偏好回填到本地（主题、默认场景、侧边栏等），跨设备一致
      syncPreferencesFromServer(userInfo.preferences)
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }

  /**
   * 清除认证信息
   */
  function clearAuth(): void {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return {
    // State
    accessToken,
    refreshToken,
    user,
    loading,
    // Getters
    isAuthenticated,
    userRole,
    isTeacher,
    isAdmin,
    needsOnboarding,
    // Actions
    login,
    register,
    refreshAccessToken,
    logout,
    fetchCurrentUser,
    clearAuth,
  }
})
