/**
 * 智慧学伴 管理路由
 * /admin/* 路径下的管理后台页面
 */
import type { RouteRecordRaw } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'

export const adminRoutes: RouteRecordRaw[] = [
  {
    path: '/admin',
    component: AppLayout,
    meta: {
      requiresAuth: true,
      allowedRoles: ['admin', 'super_admin'],
    },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: () => import('@/views/scene/DashboardView.vue'),
        meta: {
          title: '管理后台',
          requiresAuth: true,
        },
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/scene/DashboardView.vue'),
        meta: {
          title: '用户管理',
          requiresAuth: true,
        },
      },
      {
        path: 'tenants',
        name: 'AdminTenants',
        component: () => import('@/views/scene/DashboardView.vue'),
        meta: {
          title: '租户管理',
          requiresAuth: true,
        },
      },
      {
        path: 'system',
        name: 'AdminSystem',
        component: () => import('@/views/scene/DashboardView.vue'),
        meta: {
          title: '系统设置',
          requiresAuth: true,
        },
      },
      {
        path: 'audit-logs',
        name: 'AdminAuditLogs',
        component: () => import('@/views/admin/AuditLogView.vue'),
        meta: {
          title: '审计日志',
          requiresAuth: true,
        },
      },
      {
        path: 'data-governance',
        name: 'AdminDataGovernance',
        component: () => import('@/views/admin/DataGovernanceView.vue'),
        meta: {
          title: '数据治理',
          requiresAuth: true,
        },
      },
      {
        path: 'quota',
        name: 'AdminQuota',
        component: () => import('@/views/admin/QuotaDashboard.vue'),
        meta: {
          title: '配额管理',
          requiresAuth: true,
        },
      },
    ],
  },
]
