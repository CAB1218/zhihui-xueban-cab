/**
 * 智慧学伴 网络状态组合式函数
 * 全局监听在线/离线状态变化，提供响应式状态和事件回调
 *
 * 使用方式：
 * ```ts
 * const { isOnline, isOffline, onBackOnline, onGoOffline } = useNetworkStatus()
 * ```
 */
import { ref, readonly, onUnmounted } from 'vue'

/** 全局共享的在线状态（单例模式，避免重复监听） */
const isOnline = ref(navigator.onLine)

/** 全局共享的离线状态 */
const isOffline = ref(!navigator.onLine)

/** 上次断网时间戳 */
const lastOfflineTime = ref<number | null>(null)

/** 在线状态恢复回调列表 */
const onlineCallbacks: Array<() => void | Promise<void>> = []

/** 离线状态回调列表 */
const offlineCallbacks: Array<() => void | Promise<void>> = []

/** 是否已注册全局事件监听 */
let listenersRegistered = false

/**
 * 处理网络恢复事件
 */
function handleOnline(): void {
  isOnline.value = true
  isOffline.value = false
  lastOfflineTime.value = null

  // 执行所有在线恢复回调
  for (const callback of onlineCallbacks) {
    try {
      callback()
    } catch (error) {
      console.error('[NetworkStatus] Online callback error:', error)
    }
  }
}

/**
 * 处理网络断开事件
 */
function handleOffline(): void {
  isOnline.value = false
  isOffline.value = true
  lastOfflineTime.value = Date.now()

  // 执行所有离线回调
  for (const callback of offlineCallbacks) {
    try {
      callback()
    } catch (error) {
      console.error('[NetworkStatus] Offline callback error:', error)
    }
  }
}

/**
 * 注册全局网络状态监听器
 * 确保只注册一次
 */
function ensureListeners(): void {
  if (listenersRegistered) return
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  listenersRegistered = true
}

/**
 * 网络状态组合式函数
 *
 * 提供响应式的在线/离线状态，以及状态变更的回调注册
 *
 * @returns 网络状态相关属性和方法
 */
export function useNetworkStatus() {
  // 确保全局监听器已注册
  ensureListeners()

  /**
   * 注册网络恢复回调
   * 当网络从离线恢复为在线时触发
   *
   * @param callback - 恢复在线时的回调函数
   */
  function onBackOnline(callback: () => void | Promise<void>): void {
    onlineCallbacks.push(callback)
  }

  /**
   * 注册网络断开回调
   * 当网络从在线变为离线时触发
   *
   * @param callback - 断网时的回调函数
   */
  function onGoOffline(callback: () => void | Promise<void>): void {
    offlineCallbacks.push(callback)
  }

  /**
   * 获取离线持续时间（秒）
   *
   * @returns 离线秒数，如果当前在线则返回0
   */
  function getOfflineDuration(): number {
    if (isOnline.value || !lastOfflineTime.value) return 0
    return Math.floor((Date.now() - lastOfflineTime.value) / 1000)
  }

  /**
   * 格式化离线时长为可读字符串
   *
   * @returns 如 "3分钟" "1小时30分钟" 等可读字符串
   */
  function getFormattedOfflineDuration(): string {
    const seconds = getOfflineDuration()
    if (seconds < 60) return `${seconds}秒`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}分钟`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return remainingMinutes > 0 ? `${hours}小时${remainingMinutes}分钟` : `${hours}小时`
  }

  // 组件卸载时不需要移除全局监听器，因为是单例模式
  // 只需移除当前组件注册的回调
  let localOnlineCallback: (() => void | Promise<void>) | null = null
  let localOfflineCallback: (() => void | Promise<void>) | null = null

  /**
   * 在组件内注册网络恢复回调（自动清理）
   */
  function onBackOnlineAuto(callback: () => void | Promise<void>): void {
    localOnlineCallback = callback
    onBackOnline(callback)
  }

  /**
   * 在组件内注册网络断开回调（自动清理）
   */
  function onGoOfflineAuto(callback: () => void | Promise<void>): void {
    localOfflineCallback = callback
    onGoOffline(callback)
  }

  onUnmounted(() => {
    // 清理当前组件注册的回调
    if (localOnlineCallback) {
      const index = onlineCallbacks.indexOf(localOnlineCallback)
      if (index > -1) onlineCallbacks.splice(index, 1)
    }
    if (localOfflineCallback) {
      const index = offlineCallbacks.indexOf(localOfflineCallback)
      if (index > -1) offlineCallbacks.splice(index, 1)
    }
  })

  return {
    /** 是否在线 */
    isOnline: readonly(isOnline),
    /** 是否离线 */
    isOffline: readonly(isOffline),
    /** 上次断网时间戳 */
    lastOfflineTime: readonly(lastOfflineTime),
    /** 注册网络恢复回调 */
    onBackOnline,
    /** 注册网络断开回调 */
    onGoOffline,
    /** 注册网络恢复回调（组件卸载自动清理） */
    onBackOnlineAuto,
    /** 注册网络断开回调（组件卸载自动清理） */
    onGoOfflineAuto,
    /** 获取离线持续秒数 */
    getOfflineDuration,
    /** 获取格式化的离线时长 */
    getFormattedOfflineDuration,
  }
}
