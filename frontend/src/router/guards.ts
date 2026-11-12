/**
 * AI4Edu 路由守卫
 * 认证检查 + Onboarding 引导检查 + 角色权限检查
 */
import type { Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'

// Onboarding 相关路由名称
const ONBOARDING_ROUTES = new Set(['onboarding-role', 'onboarding-major', 'onboarding-interests', 'onboarding-goal'])

export function setupGuards(router: Router): void {
  /**
   * 全局前置守卫
   * - 检查认证状态
   * - 检查 Onboarding 引导状态
   * - 检查场景有效性
   * - 检查角色权限
   */
  router.beforeEach(async (to, _from, next) => {
    const authStore = useAuthStore()

    // 设置页面标题
    const title = to.meta.title as string | undefined
    document.title = title ? `${title} - 智慧学伴` : '智慧学伴智能体'

    // 不需要认证的页面直接放行
    if (to.meta.requiresAuth === false) {
      // 已登录用户访问登录/注册页，重定向到首页
      if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
        next({ path: '/' })
        return
      }
      next()
      return
    }

    // 需要认证但未登录
    if (!authStore.isAuthenticated) {
      // 尝试刷新Token（只尝试一次，失败立即清除并跳转登录，避免死循环）
      if (authStore.refreshToken) {
        try {
          await authStore.refreshAccessToken()
          // 刷新成功后获取用户信息
          await authStore.fetchCurrentUser()
        } catch {
          // Token刷新失败，清除所有认证信息，直接跳转登录
          authStore.clearAuth()
          next({
            name: 'Login',
            query: { redirect: to.fullPath },
          })
          return
        }
      }

      // 再次检查认证状态（无 refreshToken 或刷新后仍未认证）
      if (!authStore.isAuthenticated) {
        next({
          name: 'Login',
          query: { redirect: to.fullPath },
        })
        return
      }
    }

    // 已认证但未获取用户信息
    if (authStore.isAuthenticated && !authStore.user) {
      try {
        await authStore.fetchCurrentUser()
      } catch {
        authStore.clearAuth()
        next({ name: 'Login', query: { redirect: to.fullPath } })
        return
      }
    }

    // 检查 Onboarding 引导状态
    const isOnboardingRoute = to.name ? ONBOARDING_ROUTES.has(to.name as string) : false
    const userStore = useUserStore()
    // 综合判断 onboarding 状态：优先使用 authStore.user，fallback 到 userStore
    const onboardingCompleted = authStore.user?.onboarding_completed ?? userStore.onboardingCompleted

    if (authStore.user && !onboardingCompleted && !isOnboardingRoute) {
      // 未完成引导，跳转到引导页
      next({ name: 'onboarding-role' })
      return
    }

    if (onboardingCompleted && isOnboardingRoute) {
      // 已完成引导，不再允许访问引导页
      next({ path: '/' })
      return
    }

    // 检查角色权限
    const allowedRoles = (to.meta.allowedRoles ?? to.meta.roles) as string[] | undefined
    if (allowedRoles && authStore.user && authStore.user.role !== 'super_admin') {
      if (!allowedRoles.includes(authStore.user.role)) {
        next({ path: '/' })
        return
      }
    }

    next()
  })

  /**
   * 全局后置守卫
   */
  router.afterEach(() => {
    // 关闭页面加载状态
    // 可在此处添加页面访问埋点
  })
}
