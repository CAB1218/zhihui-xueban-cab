/**
 * 智慧学伴 Service Worker
 * 基于 Workbox 7.x 的 PWA 离线支持
 */

// Workbox 7.x CDN 引入
importScripts('https://storage.googleapis.com/workbox-cdn/releases/7.0.0/workbox-sw.js')

const { precaching, routing, strategies, backgroundSync, pushManager } = workbox
const { precacheAndRoute, cleanupOutdatedCaches } = precaching
const { registerRoute } = routing
const { NetworkFirst, CacheFirst, StaleWhileRevalidate } = strategies
const { Queue } = backgroundSync

// 跳过等待，立即激活
self.skipWaiting()
self.addEventListener('activate', () => {
  self.clients.claim()
})

// ============ 预缓存静态资源 ============
// 构建时由 vite-plugin-pwa 注入的预缓存清单
precacheAndRoute(self.__WB_MANIFEST || [])
cleanupOutdatedCaches()

// ============ 运行时缓存策略 ============

// API 请求：NetworkFirst（优先网络，离线回退缓存）
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/v1/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 10,
    plugins: [
      {
        cacheableResponse: {
          statuses: [0, 200],
        },
      },
      {
        expireEntries: {
          maxEntries: 100,
          maxAgeSeconds: 60 * 60, // 1小时
        },
      },
    ],
  })
)

// 静态资源（CSS/JS/字体/图片）：CacheFirst
registerRoute(
  ({ request }) =>
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'font',
  new CacheFirst({
    cacheName: 'static-assets',
    plugins: [
      {
        cacheableResponse: {
          statuses: [0, 200],
        },
      },
      {
        expireEntries: {
          maxEntries: 200,
          maxAgeSeconds: 30 * 24 * 60 * 60, // 30天
        },
      },
    ],
  })
)

// 图片资源：CacheFirst
registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: 'images-cache',
    plugins: [
      {
        cacheableResponse: {
          statuses: [0, 200],
        },
      },
      {
        expireEntries: {
          maxEntries: 100,
          maxAgeSeconds: 7 * 24 * 60 * 60, // 7天
        },
      },
    ],
  })
)

// 页面导航：NetworkFirst
registerRoute(
  ({ request }) => request.mode === 'navigate',
  new NetworkFirst({
    cacheName: 'navigation-cache',
    networkTimeoutSeconds: 5,
    plugins: [
      {
        cacheableResponse: {
          statuses: [0, 200],
        },
      },
    ],
  })
)

// CDN/第三方资源：StaleWhileRevalidate
registerRoute(
  ({ url }) =>
    url.origin === 'https://cdn.jsdelivr.net' ||
    url.origin === 'https://fonts.googleapis.com' ||
    url.origin === 'https://fonts.gstatic.com',
  new StaleWhileRevalidate({
    cacheName: 'cdn-cache',
    plugins: [
      {
        expireEntries: {
          maxEntries: 50,
          maxAgeSeconds: 7 * 24 * 60 * 60,
        },
      },
    ],
  })
)

// ============ Background Sync：离线笔记保存同步 ============
const offlineNoteQueue = new Queue('offline-note-sync', {
  onSync: async ({ queue }) => {
    let entry
    while ((entry = await queue.shiftRequest())) {
      try {
        const response = await fetch(entry.request.clone())
        if (!response.ok) {
          await queue.unshiftRequest(entry)
          return
        }
        // 通知客户端同步成功
        const clients = await self.clients.matchAll()
        clients.forEach((client) => {
          client.postMessage({
            type: 'SYNC_SUCCESS',
            payload: {
              url: entry.request.url,
              timestamp: Date.now(),
            },
          })
        })
      } catch (error) {
        // 同步失败，重新入队
        await queue.unshiftRequest(entry)
        return
      }
    }
  },
})

// 拦截离线笔记保存请求
self.addEventListener('fetch', (event) => {
  if (
    event.request.method === 'POST' &&
    event.request.url.includes('/api/v1/notes') &&
    !navigator.onLine
  ) {
    event.respondWith(
      offlineNoteQueue.pushRequest({ request: event.request }).then(() => {
        return new Response(
          JSON.stringify({
            code: 202,
            message: '笔记已保存，将在网络恢复后同步',
            data: null,
          }),
          {
            status: 202,
            headers: { 'Content-Type': 'application/json' },
          }
        )
      })
    )
    return
  }
})

// ============ Push Notification 支持 ============
self.addEventListener('push', (event) => {
  if (!event.data) return

  const data = event.data.json()
  const title = data.title || '智慧学伴 通知'
  const options = {
    body: data.body || '',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    tag: data.tag || 'default',
    data: {
      url: data.url || '/',
      type: data.type || 'general',
    },
    actions: data.actions || [],
    vibrate: [200, 100, 200],
    requireInteraction: data.requireInteraction || false,
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

// 通知点击处理
self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const urlToOpen = event.notification.data?.url || '/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // 如果已有窗口则聚焦，否则打开新窗口
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(urlToOpen)
          return client.focus()
        }
      }
      return self.clients.openWindow(urlToOpen)
    })
  )
})

// ============ 消息处理 ============
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }

  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: '1.0.0' })
  }
})
