<template>
  <div class="app-layout">
    <Sidebar v-if="showSidebar" :collapsed="sidebarCollapsed" @toggle="toggleSidebar" />
    <div class="app-layout__main" :class="{ 'app-layout__main--collapsed': sidebarCollapsed }">
      <Header />
      <main class="app-layout__content" @click="collapseSidebar">
        <router-view />
      </main>
    </div>
    <BottomNav />
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 应用布局框架
 * 包含侧边栏、顶部栏、内容区
 */
import { computed } from 'vue'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import BottomNav from './BottomNav.vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const showSidebar = computed(() => true)
const sidebarCollapsed = computed(() => userStore.preferences.sidebarCollapsed)

function toggleSidebar() {
  userStore.toggleSidebar()
}

function collapseSidebar() {
  if (!sidebarCollapsed.value) {
    userStore.updatePreferences({ sidebarCollapsed: true })
  }
}
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;

  &__main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    // 侧边栏是 fixed（220px），主区域必须让出这段宽度，否则内容会被盖住
    margin-left: 220px;
    transition: margin-left var(--transition-normal);

    &--collapsed {
      margin-left: 64px;
    }
  }

  &__content {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-lg);
    background: var(--color-bg-secondary);
  }
}

// 移动端布局
@media (max-width: 768px) {
  .app-layout {
    flex-direction: column;

    &__main {
      margin-left: 0 !important;
    }

    &__content {
      padding: var(--spacing-md);
      padding-bottom: 64px; // 底部导航高度
    }
  }
}
</style>
