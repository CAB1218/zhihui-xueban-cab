/**
 * 智慧学伴 PWA 组合式函数
 * 管理安装状态、更新提示、离线检测
 */
import { ref, onMounted, onUnmounted } from 'vue'

/** Service Worker 注册对象 */
let swRegistration: ServiceWorkerRegistration | null = null

/** 安装前事件（用于拦截浏览器默认安装提示） */
let deferredPrompt: BeforeInstallPromptEvent | null = null

/** BeforeInstallPromptEvent 类型声明 */
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

/**
 * PWA 组合式函数
 *
 * 提供安装检测、更新提示、离线状态等功能
 *
 * @returns PWA 相关状态和操作方法
 */
export function usePWA() {
  /** 是否已安装为PWA */
  const isInstalled = ref(false)

  /** 是否处于离线状态 */
  const isOffline = ref(!navigator.onLine)

  /** 是否有可用更新 */
  const updateAvailable = ref(false)

  /** 是否显示安装提示 */
  const showInstallPrompt = ref(false)

  /** 新版 Service Worker 等待激活 */
  let waitingWorker: ServiceWorker | null = null

  /**
   * 检测PWA安装状态
   */
  function checkInstallStatus() {
    // 检查是否在standalone模式运行
    const isStandalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as unknown as { standalone: boolean }).standalone === true

    // 检查是否已通过beforeinstallprompt获取安装能力
    isInstalled.value = isStandalone
  }

  /**
   * 注册Service Worker
   */
  async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) {
      console.warn('[PWA] Service Worker not supported')
      return
    }

    try {
      swRegistration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/',
      })

      // 检查更新
      swRegistration.addEventListener('updatefound', () => {
        const newWorker = swRegistration?.installing
        if (!newWorker) return

        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // 新版本已安装，等待激活
              waitingWorker = newWorker
              updateAvailable.value = true
            } else {
              // 首次安装
              console.log('[PWA] Service Worker installed for the first time')
            }
          }
        })
      })

      // 如果已有等待中的SW
      if (swRegistration.waiting) {
        waitingWorker = swRegistration.waiting
        updateAvailable.value = true
      }
    } catch (error) {
      console.error('[PWA] Service Worker registration failed:', error)
    }
  }

  /**
   * 应用更新（激活新的Service Worker）
   */
  function applyUpdate() {
    if (!waitingWorker) return

    // 通知等待中的SW跳过等待
    waitingWorker.postMessage({ type: 'SKIP_WAITING' })
    updateAvailable.value = false
    waitingWorker = null

    // 监听控制器变更，自动刷新页面
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      window.location.reload()
    })
  }

  /**
   * 触发安装提示
   */
  async function installPrompt() {
    if (!deferredPrompt) {
      console.warn('[PWA] No install prompt available')
      return
    }

    try {
      await deferredPrompt.prompt()
      const result = await deferredPrompt.userChoice

      if (result.outcome === 'accepted') {
        console.log('[PWA] User accepted the install prompt')
        isInstalled.value = true
      } else {
        console.log('[PWA] User dismissed the install prompt')
      }
    } catch (error) {
      console.error('[PWA] Install prompt error:', error)
    } finally {
      deferredPrompt = null
      showInstallPrompt.value = false
    }
  }

  /**
   * 处理在线状态变化
   */
  function handleOnline() {
    isOffline.value = false
  }

  function handleOffline() {
    isOffline.value = true
  }

  // ============ 生命周期 ============
  onMounted(() => {
    checkInstallStatus()
    registerServiceWorker()

    // 监听安装前事件
    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault()
      deferredPrompt = e as BeforeInstallPromptEvent
      showInstallPrompt.value = true
    })

    // 监听应用已安装事件
    window.addEventListener('appinstalled', () => {
      isInstalled.value = true
      deferredPrompt = null
      showInstallPrompt.value = false
    })

    // 监听在线/离线状态
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
  })

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  })

  return {
    isInstalled,
    isOffline,
    updateAvailable,
    showInstallPrompt,
    applyUpdate,
    installPrompt,
  }
}
