/**
 * AI4Edu 应用入口
 * 注册 Vue3 + Pinia + Router + Element Plus + i18n + PWA Service Worker
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import i18n from './i18n'

// 全局样式
import './styles/global.scss'

// 遥测系统
import { initTelemetry, reportVueError } from './utils/telemetry'

const app = createApp(App)

// 注册 Pinia 状态管理
const pinia = createPinia()
app.use(pinia)

// 注册 Vue Router
app.use(router)

// 注册 Element Plus（中文语言包）
app.use(ElementPlus, {
  locale: zhCn,
  size: 'default',
})

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册 i18n 国际化
app.use(i18n)

// Vue 全局错误处理器
app.config.errorHandler = (err, vm, info) => {
  reportVueError(err as Error, vm, info)
}

// 初始化遥测系统（仅生产环境）
initTelemetry()

// 挂载应用
app.mount('#app')

// ============ PWA Service Worker 注册 ============
// 只在生产构建中注册：sw.js 会对 JS/CSS 走 CacheFirst（30 天），
// 在开发环境注册会把 Vite 的模块缓存成旧版本，改完代码页面却仍是旧内容甚至白屏。
// 开发环境反过来自动注销历史遗留的 SW 并清空缓存，避免浏览器一直卡在旧版本。
const IS_PROD = import.meta.env.PROD

if (!IS_PROD && 'serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((regs) => {
    regs.forEach((reg) => {
      reg.unregister()
      console.log('[PWA] 开发环境已注销历史 Service Worker')
    })
  })
  if (typeof caches !== 'undefined') {
    caches.keys().then((keys) => {
      keys.forEach((key) => caches.delete(key))
    })
  }
}

if (IS_PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/',
      })

      console.log('[PWA] Service Worker registered successfully, scope:', registration.scope)

      // 检查更新
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        if (!newWorker) return

        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // 新版本已就绪，通知用户
            console.log('[PWA] New version available')
          }
        })
      })

      // 监听 Service Worker 发来的消息
      navigator.serviceWorker.addEventListener('message', (event) => {
        const data = event.data

        if (!data || !data.type) return

        switch (data.type) {
          case 'SYNC_SUCCESS':
            console.log('[PWA] Offline data synced:', data.payload)
            // 触发自定义事件通知 UI 组件
            window.dispatchEvent(
              new CustomEvent('pwa:sync-success', { detail: data.payload })
            )
            break

          case 'OFFLINE_ACTION_SYNCED':
            console.log('[PWA] Offline action synced:', data.payload)
            window.dispatchEvent(
              new CustomEvent('pwa:action-synced', { detail: data.payload })
            )
            break
        }
      })
    } catch (error) {
      console.error('[PWA] Service Worker registration failed:', error)
    }
  })
}
