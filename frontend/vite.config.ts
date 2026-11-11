import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { resolve } from 'path'

/**
 * 开发环境拦截 /sw.js，返回一个"自毁"的 Service Worker。
 *
 * 背景：public/sw.js 是基于 Workbox 的 PWA 缓存，对 JS/CSS 走 CacheFirst（30 天）。
 * 浏览器在开发环境访问过之后会一直有 SW 接管，导致改了代码页面仍是旧内容甚至白屏。
 * 这里在 dev 下把 /sw.js 换成一个会清空缓存、注销自身并刷新页面的脚本，
 * 老浏览器更新一次即可自动恢复（生产构建仍然使用 public/sw.js 原文）。
 */
function devKillServiceWorker() {
  const killSwitch = `
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys()
      await Promise.all(keys.map((key) => caches.delete(key)))
    } catch (e) {}
    try { await self.registration.unregister() } catch (e) {}
    const clients = await self.clients.matchAll({ type: 'window' })
    clients.forEach((client) => client.navigate(client.url))
  })())
})
`
  return {
    name: 'dev-kill-service-worker',
    apply: 'serve' as const,
    configureServer(server: any) {
      server.middlewares.use('/sw.js', (_req: any, res: any) => {
        res.setHeader('Content-Type', 'application/javascript')
        res.setHeader('Cache-Control', 'no-store')
        res.end(killSwitch)
      })
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    devKillServiceWorker(),
    vue(),
    VitePWA({
      /** 使用项目自定义的 Service Worker */
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      /** 是否启用 PWA（开发模式默认关闭） */
      disabled: process.env.NODE_ENV === 'development',
      /** Service Worker 注册类型 */
      registerType: 'autoUpdate',
      /** Web App Manifest 配置 */
      manifest: {
        name: 'AI4Edu - 智慧教学平台',
        short_name: 'AI4Edu',
        description: 'AI驱动的智慧教学平台，支持课堂互动、智能辅导与个性化学习',
        theme_color: '#1976D2',
        background_color: '#FFFFFF',
        display: 'standalone',
        orientation: 'any',
        start_url: '/',
        scope: '/',
        lang: 'zh-CN',
        dir: 'ltr',
        categories: ['education', 'productivity'],
        icons: [
          {
            src: '/icons/icon-72x72.png',
            sizes: '72x72',
            type: 'image/png',
          },
          {
            src: '/icons/icon-96x96.png',
            sizes: '96x96',
            type: 'image/png',
          },
          {
            src: '/icons/icon-128x128.png',
            sizes: '128x128',
            type: 'image/png',
          },
          {
            src: '/icons/icon-144x144.png',
            sizes: '144x144',
            type: 'image/png',
          },
          {
            src: '/icons/icon-152x152.png',
            sizes: '152x152',
            type: 'image/png',
          },
          {
            src: '/icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-384x384.png',
            sizes: '384x384',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
        shortcuts: [
          {
            name: '课堂模式',
            short_name: '课堂',
            url: '/classroom',
            icons: [{ src: '/icons/icon-96x96.png', sizes: '96x96' }],
          },
          {
            name: 'AI 学伴',
            short_name: '学伴',
            url: '/study-buddy',
            icons: [{ src: '/icons/icon-96x96.png', sizes: '96x96' }],
          },
        ],
      },
      /** 开发模式配置 */
      devOptions: {
        enabled: false,
      },
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0', // 同时监听IPv4和IPv6
    allowedHosts: true, // 允许所有 host（支持 ngrok/cloudflared 隧道）
    proxy: {
      // 代理后端API请求
      '/api': {
        target: 'http://127.0.0.1:8000', // 使用IPv4地址避免localhost解析到IPv6
        changeOrigin: true,
      },
      // 代理WebSocket
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables" as *;\n`,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (/node_modules\/(vue|vue-router|pinia)\//.test(id)) return 'vue'
          if (id.includes('node_modules/element-plus/')) return 'elementPlus'
          if (/node_modules\/(echarts|vue-echarts)\//.test(id)) return 'echarts'
        },
      },
    },
  },
})
