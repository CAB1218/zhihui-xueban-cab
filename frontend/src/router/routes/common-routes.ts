/**
 * 通用设置路由
 * /profile 个人设置、/preferences 偏好设置、/help 帮助中心
 * 头像下拉菜单直接跳这三个地址，不再依赖场景前缀
 */
import type { RouteRecordRaw } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'

export const commonRoutes: RouteRecordRaw[] = [
  {
    path: '/profile',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'ProfileSettings',
        component: () => import('@/views/user/ProfileSettingsView.vue'),
        meta: {
          title: '个人设置',
          requiresAuth: true,
        },
      },
    ],
  },
  {
    path: '/preferences',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'PreferenceSettings',
        component: () => import('@/views/user/PreferenceSettingsView.vue'),
        meta: {
          title: '偏好设置',
          requiresAuth: true,
        },
      },
    ],
  },
  {
    path: '/help',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'HelpCenterStandalone',
        component: () => import('@/views/help/HelpCenterView.vue'),
        meta: {
          title: '帮助中心',
          requiresAuth: true,
        },
      },
    ],
  },
]
