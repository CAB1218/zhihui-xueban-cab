/**
 * AI4Edu 路由配置
 * 场景化嵌套路由结构
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { setupGuards } from './guards'
import { sceneRoutes } from './routes/scene-routes'
import { teacherRoutes } from './routes/teacher-routes'
import { adminRoutes } from './routes/admin-routes'
import { commonRoutes } from './routes/common-routes'

// 静态路由（无需认证）
const constantRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: {
      title: '登录',
      requiresAuth: false,
    },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: {
      title: '注册',
      requiresAuth: false,
    },
  },
  {
    path: '/onboarding',
    component: () => import('@/views/onboarding/OnboardingLayout.vue'),
    meta: {
      title: '引导',
      requiresAuth: true,
    },
    children: [
      {
        path: 'role',
        name: 'onboarding-role',
        component: () => import('@/views/onboarding/StepRoleView.vue'),
        meta: {
          title: '选择角色',
          requiresAuth: true,
        },
      },
      {
        path: 'major',
        name: 'onboarding-major',
        component: () => import('@/views/onboarding/StepMajorView.vue'),
        meta: {
          title: '所在专业',
          requiresAuth: true,
        },
      },
      {
        path: 'interests',
        name: 'onboarding-interests',
        component: () => import('@/views/onboarding/StepInterestsView.vue'),
        meta: {
          title: '兴趣学科',
          requiresAuth: true,
        },
      },
      {
        path: 'goal',
        name: 'onboarding-goal',
        component: () => import('@/views/onboarding/StepGoalView.vue'),
        meta: {
          title: '学习目标',
          requiresAuth: true,
        },
      },
    ],
  },
]

// 动态路由（需认证）
const asyncRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    // 尊重「偏好设置 → 默认进入的场景」，没有设置时回落到课堂仪表盘
    redirect: () => {
      try {
        const prefs = JSON.parse(localStorage.getItem('user_preferences') || '{}')
        const scenes = ['classroom', 'self-study', 'exam', 'discussion']
        const scene = scenes.includes(prefs?.defaultScene) ? prefs.defaultScene : 'classroom'
        return `/scene/${scene}/dashboard`
      } catch {
        return '/scene/classroom/dashboard'
      }
    },
  },
  // 少写场景前缀时的兼容入口（用独立跳转路由，避免 alias 与动态参数冲突报警告）
  {
    path: '/analysis',
    redirect: '/scene/classroom/analysis',
  },
  {
    path: '/curriculum',
    redirect: '/scene/classroom/curriculum',
  },
  {
    path: '/advice',
    redirect: '/scene/classroom/advice',
  },
  ...sceneRoutes,
  ...teacherRoutes,
  ...adminRoutes,
  ...commonRoutes,
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    // 独立的 404 页：不能用 DashboardView 兜底，否则会出现
    // 「标题是页面不存在、内容却是课堂仪表盘」的误导性页面
    component: () => import('@/views/error/NotFoundView.vue'),
    meta: {
      title: '页面不存在',
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: [...constantRoutes, ...asyncRoutes],
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  },
})

// 设置路由守卫
setupGuards(router)

export default router
