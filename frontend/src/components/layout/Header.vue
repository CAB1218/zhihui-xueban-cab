<template>
  <header class="header">
    <div class="header__left">
      <slot name="scene-switcher" />
      <h2 class="header__title">{{ pageTitle }}</h2>
    </div>

    <div class="header__right">
      <!-- 搜索框（集成 SearchBox 组件 + Ctrl+K） -->
      <SearchBox class="header__search hidden-mobile" />

      <!-- 通知 -->
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="header__notification">
        <el-button :icon="Bell" circle size="default" @click="handleNotifications" />
      </el-badge>

      <!-- 用户菜单 -->
      <el-dropdown trigger="click" @command="handleUserCommand">
        <div class="header__user">
          <el-avatar :size="32" :src="userAvatar">
            {{ userInitial }}
          </el-avatar>
          <span class="header__username hidden-mobile">{{ userName }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人设置</el-dropdown-item>
            <el-dropdown-item command="preferences">偏好设置</el-dropdown-item>
            <el-dropdown-item command="help">帮助中心</el-dropdown-item>
            <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * AI4Edu 顶部栏
 * 包含搜索、通知、用户菜单
 */
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import SearchBox from '@/components/search/SearchBox.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const unreadCount = ref<number>(0)

const userName = computed(() => authStore.user?.nickname ?? '用户')
const userAvatar = computed(() => authStore.user?.avatar_url ?? '')
const userInitial = computed(() => userName.value.charAt(0))

const pageTitle = computed(() => {
  const title = route.meta.title as string | undefined
  return title ?? ''
})

function handleNotifications(): void {
  // TODO: 跳转通知页面
}

async function handleUserCommand(command: string): Promise<void> {
  switch (command) {
    case 'profile':
      router.push({ name: 'ProfileSettings' })
      break
    case 'preferences':
      router.push({ name: 'PreferenceSettings' })
      break
    case 'help':
      router.push({ name: 'HelpCenterStandalone' })
      break
    case 'logout':
      await authStore.logout()
      break
  }
}
</script>

<style lang="scss" scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 var(--spacing-lg);
  background: var(--color-bg-primary);
  border-bottom: 2px solid var(--scene-primary-color, #1976D2);
  box-shadow: var(--shadow-sm);

  &__left {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-primary);
  }

  &__right {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  &__search {
    width: 240px;
  }

  &__notification {
    cursor: pointer;
  }

  &__user {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
    padding: 4px 8px;
    border-radius: var(--border-radius-md);
    transition: background-color var(--transition-fast);

    &:hover {
      background-color: var(--color-bg-secondary);
    }
  }

  &__username {
    font-size: 14px;
    color: var(--color-text-regular);
  }
}
</style>
