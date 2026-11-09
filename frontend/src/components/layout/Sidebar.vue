<template>
  <aside :class="['sidebar', { 'sidebar--collapsed': collapsed }]">
    <div class="sidebar__logo" @click="$router.push('/')">
      <img src="/favicon.svg" alt="AI4Edu" class="sidebar__logo-img" />
      <span v-show="!collapsed" class="sidebar__logo-text">AI4Edu</span>
    </div>

    <el-menu
      :default-active="activeMenu"
      :collapse="collapsed"
      :collapse-transition="true"
      router
      class="sidebar__menu"
      background-color="transparent"
      text-color="rgba(255, 255, 255, 0.8)"
      active-text-color="#FFFFFF"
    >
      <el-menu-item index="/scene/classroom/dashboard" @click="navigateTo('/scene/classroom/dashboard')">
        <el-icon><School /></el-icon>
        <template #title>课堂模式</template>
      </el-menu-item>

      <el-menu-item index="/scene/self_study/dashboard" @click="navigateTo('/scene/self_study/dashboard')">
        <el-icon><Reading /></el-icon>
        <template #title>自习模式</template>
      </el-menu-item>

      <el-menu-item index="/scene/exam/dashboard" @click="navigateTo('/scene/exam/dashboard')">
        <el-icon><EditPen /></el-icon>
        <template #title>考前模式</template>
      </el-menu-item>

      <el-menu-item index="/scene/discussion/dashboard" @click="navigateTo('/scene/discussion/dashboard')">
        <el-icon><ChatDotRound /></el-icon>
        <template #title>讨论模式</template>
      </el-menu-item>

      <el-divider v-if="showTeacherMenu" />

      <el-menu-item v-if="showTeacherMenu" index="/teacher">
        <el-icon><User /></el-icon>
        <template #title>教师工作台</template>
      </el-menu-item>

      <el-divider />

      <el-menu-item-group title="功能">
        <el-menu-item
          v-for="item in featureMenus"
          :key="item.index"
          :index="item.index"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu-item-group>
    </el-menu>

    <div class="sidebar__footer">
      <el-button
        :icon="collapsed ? 'Expand' : 'Fold'"
        circle
        size="small"
        @click="$emit('toggle')"
      />
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * AI4Edu 侧边栏
 * 支持折叠/展开，根据用户角色显示不同菜单
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

defineProps<{
  collapsed: boolean
}>()

defineEmits<{
  toggle: []
}>()

const route = useRoute()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)
const showTeacherMenu = computed(() => authStore.isTeacher || authStore.isAdmin)

/** 当前场景类型，用于构建功能链接 */
const currentSceneType = computed(() => {
  const m = route.path.match(/^\/scene\/([^/]+)/)
  return m ? m[1] : 'self_study'
})

/** 功能菜单列表 */
const featureMenus = computed(() => [
  { index: `/scene/${currentSceneType.value}/curriculum`, icon: 'Reading', title: '课程梳理' },
  { index: `/scene/${currentSceneType.value}/graphs`, icon: 'Connection', title: '知识图谱' },
  { index: `/scene/${currentSceneType.value}/notes`, icon: 'EditPen', title: '智能笔记' },
  { index: `/scene/${currentSceneType.value}/resources`, icon: 'Folder', title: '资源管理' },
  { index: `/scene/${currentSceneType.value}/agent`, icon: 'ChatLineSquare', title: 'AI 智能体中心' },
  { index: `/scene/${currentSceneType.value}/search`, icon: 'Search', title: '全局搜索' },
  { index: `/scene/${currentSceneType.value}/growth-profile`, icon: 'TrendCharts', title: '成长档案' },
])

</script>

<style lang="scss" scoped>
.sidebar {
  width: 220px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: white;
  transition: width var(--transition-normal);
  overflow: hidden;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;

  &--collapsed {
    width: 64px;
  }

  &__logo {
    display: flex;
    align-items: center;
    padding: 16px;
    gap: 12px;
    cursor: pointer;
    height: 64px;
  }

  &__logo-img {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
  }

  &__logo-text {
    font-size: 18px;
    font-weight: 700;
    white-space: nowrap;
  }

  &__menu {
    flex: 1;
    border-right: none;
    overflow-y: auto;
  }

  &__footer {
    padding: 12px;
    display: flex;
    justify-content: center;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
  }
}
</style>
