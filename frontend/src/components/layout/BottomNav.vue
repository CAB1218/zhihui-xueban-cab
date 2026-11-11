<template>
  <nav class="bottom-nav hidden-desktop">
    <router-link
      v-for="item in navItems"
      :key="item.path"
      :to="item.path"
      :class="['bottom-nav__item', { 'bottom-nav__item--active': isActive(item.path) }]"
    >
      <el-icon :size="20"><component :is="item.icon" /></el-icon>
      <span class="bottom-nav__label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
/**
 * AI4Edu 底部导航（移动端）
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/** 底部导航项 */
interface NavItem {
  path: string
  icon: string
  label: string
}

const route = useRoute()
const authStore = useAuthStore()

/** 当前场景类型 */
const currentSceneType = computed(() => {
  const m = route.path.match(/^\/scene\/([^/]+)/)
  return m ? m[1] : 'self_study'
})

const navItems = computed<NavItem[]>(() => {
  const scene = currentSceneType.value
  const items: NavItem[] = [
    { path: `/scene/${scene}/dashboard`, icon: 'HomeFilled', label: '首页' },
    { path: `/scene/${scene}/graphs`, icon: 'Connection', label: '图谱' },
    { path: `/scene/${scene}/notes`, icon: 'EditPen', label: '笔记' },
    { path: `/scene/${scene}/resources`, icon: 'Folder', label: '资源' },
  ]

  if (authStore.isTeacher || authStore.isAdmin) {
    items.push({ path: '/teacher', icon: 'User', label: '教师' })
  }

  return items
})

function isActive(path: string): boolean {
  return route.path.startsWith(path)
}
</script>

<style lang="scss" scoped>
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: var(--color-bg-primary);
  border-top: 1px solid var(--color-border);
  z-index: 1000;

  &__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 12px;
    color: var(--color-text-secondary);
    text-decoration: none;
    transition: color var(--transition-fast);

    &--active {
      color: var(--scene-primary-color);
    }
  }

  &__label {
    font-size: 11px;
    line-height: 1;
  }
}
</style>
