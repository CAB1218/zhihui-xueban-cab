<template>
  <Transition name="offline-slide">
    <div v-if="isOffline" class="offline-alert" :class="{ 'offline-alert--syncing': isSyncing }">
      <div class="offline-alert__content">
        <el-icon class="offline-alert__icon" :size="18">
          <component :is="isSyncing ? 'Loading' : 'WarningFilled'" />
        </el-icon>
        <span class="offline-alert__text">
          <template v-if="isSyncing">
            正在同步离线数据...
          </template>
          <template v-else-if="pendingCount > 0">
            网络不可用 · {{ pendingCount }} 条操作待同步
          </template>
          <template v-else>
            网络不可用 · 部分功能受限
          </template>
        </span>
        <span v-if="!isSyncing && offlineDuration" class="offline-alert__duration">
          已离线 {{ offlineDuration }}
        </span>
      </div>
    </div>
  </Transition>

  <!-- 网络恢复提示 -->
  <Transition name="online-toast">
    <div v-if="showBackOnline" class="online-toast">
      <div class="online-toast__content">
        <el-icon class="online-toast__icon" :size="18">
          <SuccessFilled />
        </el-icon>
        <span class="online-toast__text">
          网络已恢复{{ syncedCount > 0 ? `，${syncedCount} 条操作已同步` : '' }}
        </span>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
/**
 * AI4Edu 离线提示组件
 * 当网络不可用时在页面顶部显示提示横幅，
 * 网络恢复时短暂显示成功提示
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { SuccessFilled } from '@element-plus/icons-vue'
import { useNetworkStatus } from '@/composables/useNetworkStatus'
import { getPendingCount, processQueue } from '@/utils/offlineQueue'

const {
  isOffline,
  onBackOnlineAuto,
  onGoOfflineAuto,
  getFormattedOfflineDuration,
} = useNetworkStatus()

/** 离线时长显示文本 */
const offlineDuration = ref<string>('')

/** 离线期间待同步操作数 */
const pendingCount = ref<number>(0)

/** 是否正在同步数据 */
const isSyncing = ref<boolean>(false)

/** 是否显示网络恢复提示 */
const showBackOnline = ref<boolean>(false)

/** 网络恢复时已同步的操作数 */
const syncedCount = ref<number>(0)

/** 离线时长更新定时器 */
let durationTimer: ReturnType<typeof setInterval> | null = null

/**
 * 更新离线时长显示
 */
function updateOfflineDuration(): void {
  if (isOffline.value) {
    offlineDuration.value = getFormattedOfflineDuration()
  }
}

/**
 * 更新待同步操作数
 */
async function updatePendingCount(): Promise<void> {
  try {
    pendingCount.value = await getPendingCount()
  } catch {
    pendingCount.value = 0
  }
}

// 注册回调：网络断开
onGoOfflineAuto(() => {
  updatePendingCount()
  updateOfflineDuration()
  // 每30秒更新离线时长
  durationTimer = setInterval(updateOfflineDuration, 30000)
})

// 注册回调：网络恢复
onBackOnlineAuto(async () => {
  // 停止更新离线时长
  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }
  offlineDuration.value = ''

  // 开始同步离线队列
  isSyncing.value = true
  const count = pendingCount.value

  try {
    await processQueue()
    syncedCount.value = count
  } catch (error) {
    console.error('[OfflineAlert] Sync failed:', error)
    syncedCount.value = 0
  } finally {
    isSyncing.value = false
    pendingCount.value = 0
  }

  // 显示恢复提示
  showBackOnline.value = true
  setTimeout(() => {
    showBackOnline.value = false
    syncedCount.value = 0
  }, 4000)
})

// 组件挂载时初始化
onMounted(() => {
  if (isOffline.value) {
    updatePendingCount()
    updateOfflineDuration()
    durationTimer = setInterval(updateOfflineDuration, 30000)
  }
})

// 组件卸载时清理
onUnmounted(() => {
  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }
})
</script>

<style lang="scss" scoped>
/* 离线提示横幅 */
.offline-alert {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: #E65100;
  color: #fff;
  padding: 8px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);

  &--syncing {
    background: #1565C0;
  }

  &__content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    max-width: 1200px;
    margin: 0 auto;
    font-size: 14px;
  }

  &__icon {
    flex-shrink: 0;
  }

  &__text {
    font-weight: 500;
  }

  &__duration {
    font-size: 12px;
    opacity: 0.85;
    margin-left: 8px;
  }
}

/* 离线横幅滑入/滑出动画 */
.offline-slide-enter-active,
.offline-slide-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.offline-slide-enter-from,
.offline-slide-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

/* 网络恢复提示 */
.online-toast {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  background: #2E7D32;
  color: #fff;
  padding: 10px 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);

  &__content {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    white-space: nowrap;
  }

  &__icon {
    flex-shrink: 0;
  }

  &__text {
    font-weight: 500;
  }
}

/* 恢复提示淡入/淡出动画 */
.online-toast-enter-active,
.online-toast-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.online-toast-enter-from,
.online-toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-12px);
}

/* 同步中的旋转动画 */
:deep(.el-icon.is-loading) {
  animation: rotating 1.5s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
