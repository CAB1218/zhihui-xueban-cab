/**
 * AI4Edu 场景化路由定义
 * 核心路由结构：/scene/:sceneType/*
 * 包含 SceneRouterView 场景路由容器
 */
import type { RouteRecordRaw } from 'vue-router'
import SceneLayout from '@/components/layout/SceneLayout.vue'

export const sceneRoutes: RouteRecordRaw[] = [
  {
    path: '/scene/:sceneType',
    component: SceneLayout,
    meta: {
      requiresAuth: true,
    },
    children: [
      {
        // /scene/:sceneType 直接访问时补全到仪表盘，避免空白页
        path: '',
        name: 'SceneIndex',
        redirect: (to) => `/scene/${to.params.sceneType}/dashboard`,
        meta: {
          requiresAuth: true,
        },
      },
      {
        path: 'dashboard',
        name: 'SceneDashboard',
        component: () => import('@/views/scene/DashboardView.vue'),
        meta: {
          title: '场景仪表盘',
          requiresAuth: true,
        },
      },
      {
        path: 'note/:id',
        name: 'SceneNote',
        component: () => import('@/views/note/NoteEditView.vue'),
        meta: {
          title: '笔记编辑',
          requiresAuth: true,
        },
      },
      {
        // ========== 课堂互动（大厅 + 房间）==========
        path: 'classroom',
        name: 'SceneClassroom',
        component: () => import('@/views/scene/classroom/ClassroomRoomView.vue'),
        meta: {
          title: '课堂互动',
          requiresAuth: true,
          allowedRoles: ['student', 'teacher', 'admin'],
        },
      },
      {
        path: 'classroom/:classroomId',
        name: 'SceneClassroomRoom',
        component: () => import('@/views/scene/classroom/ClassroomRoomView.vue'),
        meta: {
          title: '课堂互动',
          requiresAuth: true,
          allowedRoles: ['student', 'teacher', 'admin'],
        },
      },
      {
        path: 'resource/:id',
        name: 'SceneResource',
        component: () => import('@/views/resource/ResourceDetailView.vue'),
        meta: {
          title: '资源详情',
          requiresAuth: true,
        },
      },
      {
        // ========== 学情分析（数据质量检查 + 个体/群体摘要）==========
        path: 'analysis',
        name: 'SceneLearningAnalysis',
        component: () => import('@/views/analysis/LearningAnalysisView.vue'),
        meta: {
          title: '学情分析',
          requiresAuth: true,
          allowedRoles: ['student', 'teacher', 'admin', 'super_admin'],
        },
      },
      {
        // ========== 课程梳理（理解学科-学习内容与要求梳理） ==========
        path: 'curriculum',
        name: 'SceneCurriculum',
        component: () => import('@/views/curriculum/CurriculumOutlineView.vue'),
        meta: {
          title: '课程梳理',
          requiresAuth: true,
          allowedRoles: ['student', 'teacher', 'admin'],
        },
      },
      {
        // ========== 个性化学习建议（任务3）==========
        path: 'advice',
        name: 'SceneLearningAdvice',
        component: () => import('@/views/advice/LearningAdviceView.vue'),
        meta: {
          title: '个性化学习建议',
          requiresAuth: true,
          allowedRoles: ['student', 'teacher', 'admin', 'super_admin'],
        },
      },
      {
        // ========== AI 智能体中心入口 ==========
        path: 'agent',
        name: 'AgentCenter',
        component: () => import('@/views/agent/AgentCenterView.vue'),
        meta: {
          title: 'AI智能体中心',
          requiresAuth: true,
        },
      },
      {
        path: 'ai-chat/:sessionId?',
        name: 'SceneAIChat',
        component: () => import('@/views/agent/AgentChatView.vue'),
        meta: {
          title: 'AI对话',
          requiresAuth: true,
        },
      },
      {
        path: 'diagnosis/:id?',
        name: 'SceneDiagnosis',
        component: () => import('@/views/diagnosis/DiagnosisView.vue'),
        meta: {
          title: '学习诊断',
          requiresAuth: true,
        },
      },
      // ========== T03 新增路由 ==========
      {
        path: 'graphs',
        name: 'GraphSquare',
        component: () => import('@/views/graph/GraphSquareView.vue'),
        meta: {
          title: '知识图谱广场',
          requiresAuth: true,
        },
      },
      {
        path: 'graph/cross-subject',
        name: 'CrossSubjectGraph',
        component: () => import('@/views/graph/CrossSubjectGraphView.vue'),
        meta: {
          title: '跨学科关联图谱',
          requiresAuth: true,
          allowedRoles: ['student', 'teacher', 'admin', 'super_admin'],
        },
      },
      {
        path: 'graph/:id',
        name: 'GraphDetail',
        component: () => import('@/views/graph/GraphDetailView.vue'),
        meta: {
          title: '图谱详情',
          requiresAuth: true,
        },
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('@/views/search/SearchView.vue'),
        meta: {
          title: '搜索',
          requiresAuth: true,
          allowedRoles: ['student', 'teacher'],
        },
      },
      {
        path: 'resources',
        name: 'MyResources',
        component: () => import('@/views/resource/MyResourcesView.vue'),
        meta: {
          title: '我的资源',
          requiresAuth: true,
        },
      },
      {
        path: 'resources/upload',
        name: 'ResourceUpload',
        component: () => import('@/views/resource/ResourceUploadView.vue'),
        meta: {
          title: '上传资源',
          requiresAuth: true,
        },
      },
      {
        path: 'resources/:id',
        name: 'ResourceDetail',
        component: () => import('@/views/resource/ResourceDetailView.vue'),
        meta: {
          title: '资源详情',
          requiresAuth: true,
        },
      },
      // ========== T04 新增路由 ==========
      {
        path: 'notes',
        name: 'NoteList',
        component: () => import('@/views/note/NoteListView.vue'),
        meta: {
          title: '笔记列表',
          requiresAuth: true,
        },
      },
      {
        path: 'buddy',
        name: 'BuddyChat',
        component: () => import('@/views/buddy/BuddyChatView.vue'),
        meta: {
          title: '学伴聊天',
          requiresAuth: true,
        },
      },
      {
        path: 'help',
        name: 'HelpCenter',
        component: () => import('@/views/help/HelpCenterView.vue'),
        meta: {
          title: '帮助中心',
          requiresAuth: false,
        },
      },
      {
        path: 'growth-profile',
        name: 'GrowthProfile',
        component: () => import('@/views/growth/GrowthProfileView.vue'),
        meta: {
          title: '成长档案',
          requiresAuth: true,
          allowedRoles: ['student', 'teacher', 'admin'],
        },
      },
    ],
  },
]
