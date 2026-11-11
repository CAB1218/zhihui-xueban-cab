<template>
  <div :class="['scene-layout', sceneClass]">
    <Sidebar v-if="showSidebar" :collapsed="sidebarCollapsed" @toggle="toggleSidebar" />
    <div class="scene-layout__main" :class="{ 'scene-layout__main--collapsed': sidebarCollapsed }">
      <Header>
        <template #scene-switcher>
          <div class="scene-switcher">
            <el-dropdown trigger="click" @command="handleSceneSwitch">
              <el-button :style="{ backgroundColor: primaryColor, borderColor: primaryColor }" round>
                <el-icon class="mr-1"><component :is="sceneIcon" /></el-icon>
                {{ sceneName }}
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="scene in sceneList"
                    :key="scene.scene_type"
                    :command="scene.scene_type"
                    :class="{ 'is-active': scene.scene_type === currentSceneType }"
                  >
                    <el-icon><component :is="sceneIconMap[scene.icon] || 'School'" /></el-icon>
                    {{ scene.name }}
                    <el-tag v-if="scene.scene_type === currentSceneType" type="success" size="small" style="margin-left: 8px;">
                      当前
                    </el-tag>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>

            <!-- 场景推荐 -->
            <el-popover v-if="recommendation" placement="bottom" :width="260" trigger="hover">
              <template #reference>
                <el-badge is-dot class="scene-switcher__recommendation-badge">
                  <el-button circle size="small" :icon="'MagicStick'" />
                </el-badge>
              </template>
              <div class="scene-switcher__recommendation">
                <p>{{ recommendation.reason }}</p>
                <el-button
                  v-if="recommendation.recommended_scene !== currentSceneType"
                  type="primary"
                  size="small"
                  @click="switchToRecommended"
                >
                  切换到{{ getSceneName(recommendation.recommended_scene) }}
                </el-button>
              </div>
            </el-popover>
          </div>
        </template>
      </Header>
      <main class="scene-layout__content" @click="collapseSidebar">
        <router-view />
      </main>
    </div>
    <BottomNav />
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 场景化布局
 * 根据当前场景动态切换主题样式
 */
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import BottomNav from './BottomNav.vue'
import { useSceneStore } from '@/stores/scene'
import { useUserStore } from '@/stores/user'
import { SceneType, SCENE_CONFIG } from '@/utils/constants'

const route = useRoute()
const router = useRouter()
const sceneStore = useSceneStore()
const userStore = useUserStore()

const showSidebar = computed(() => true)
const sidebarCollapsed = computed(() => userStore.preferences.sidebarCollapsed)
const currentSceneType = computed(() => sceneStore.currentSceneType)
const primaryColor = computed(() => sceneStore.primaryColor)
const sceneName = computed(() => sceneStore.sceneName)
const sceneList = computed(() => sceneStore.sceneList)
const sceneClass = computed(() => sceneStore.sceneClass)
const recommendation = computed(() => sceneStore.recommendation)

const sceneIconMap: Record<string, string> = {
  school: 'School',
  menu_book: 'Reading',
  quiz: 'EditPen',
  forum: 'ChatDotRound',
}

const sceneIcon = computed(() => {
  const config = SCENE_CONFIG[currentSceneType.value as SceneType]
  const iconName = config?.icon || 'school'
  return sceneIconMap[iconName] || 'School'
})

const SCENE_NAMES: Record<string, string> = {
  classroom: '课堂模式',
  self_study: '自习模式',
  exam: '考前模式',
  discussion: '讨论模式',
}

function getSceneName(sceneType: string): string {
  return SCENE_NAMES[sceneType] || sceneType
}

// 从路由参数获取场景类型
watch(
  () => route.params.sceneType,
  (newSceneType) => {
    if (newSceneType && isValidSceneType(newSceneType as string)) {
      sceneStore.switchScene(newSceneType as SceneType)
    }
  },
  { immediate: true }
)

onMounted(async () => {
  await sceneStore.fetchSceneList()
  // 应用场景主题
  sceneStore.applySceneTheme()
  // 获取推荐
  await sceneStore.getRecommendation()
})

function isValidSceneType(type: string): boolean {
  return Object.values(SceneType).includes(type as SceneType)
}

async function handleSceneSwitch(sceneType: string): Promise<void> {
  await sceneStore.switchScene(sceneType as SceneType)
  // 更新路由
  const currentPath = route.path
  const newPath = currentPath.replace(/\/scene\/\w+/, `/scene/${sceneType}`)
  if (newPath !== currentPath) {
    router.push(newPath)
  }
}

async function switchToRecommended(): Promise<void> {
  if (recommendation.value) {
    await handleSceneSwitch(recommendation.value.recommended_scene)
  }
}

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
.scene-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;

  &__main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    /* Sidebar 用 position: fixed 脱离文档流，主体必须主动让出宽度，
       否则内容会钻到侧边栏下面被遮挡 */
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

.scene-switcher {
  display: flex;
  align-items: center;
  gap: 8px;

  .el-button {
    color: white;
  }

  &__recommendation-badge {
    :deep(.el-badge__content) {
      background-color: var(--el-color-warning);
    }
  }

  &__recommendation {
    p {
      margin-bottom: 10px;
      font-size: 14px;
      color: #666;
      line-height: 1.5;
    }
  }
}

@media (max-width: 768px) {
  .scene-layout {
    flex-direction: column;

    &__main {
      margin-left: 0 !important;
    }

    &__content {
      padding: var(--spacing-md);
      padding-bottom: 64px;
    }
  }
}
</style>
