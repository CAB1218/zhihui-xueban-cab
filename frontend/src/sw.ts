/**
 * AI4Edu Service Worker
 * 基于 Workbox 7.x 的 PWA 离线支持
 *
 * 缓存策略：
 * - 静态资源（CSS/JS/字体）：CacheFirst（优先缓存，30天有效期）
 * - API 数据：NetworkFirst（优先网络，超时10s回退缓存）
 * - 图片：StaleWhileRevalidate（先返回缓存，后台更新）
 * - 页面导航：NetworkFirst（优先网络，离线回退）
 * - CDN/第三方资源：StaleWhileRevalidate
 *
 * 附加功能：
 * - 离线笔记保存同步（Background Sync Queue）
 * - 推送通知支持
 * - 离线页面回退
 */

declare const self: ServiceWorkerGlobalScope

// ============ 预缓存 ============
// 由 vite-plugin-pwa 在构建时注入
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching'

// 预缓存构建产物
precacheAndRoute(self.__WB_MANIFEST || [])
// 清理旧版本缓存
cleanupOutdatedCaches()

// ============ 跳过等待 & 立即激活 ============
self.skipWaiting()
self.addEventListener('activate', () => {
  self.clients.claim()
})

// ============ 运行时缓存策略 ============
import { registerRoute } from 'workbox-routing'
import { NetworkFirst, CacheFirst, StaleWhileRevalidate } from 'workbox-strategies'
import { ExpirationPlugin } from 'workbox-expiration'
import { CacheableResponsePlugin } from 'workbox-cacheable-response'

// ---- API 请求：NetworkFirst（优先网络，离线回退缓存） ----
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/v1/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 10,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 60 * 60, // 1小时
      }),
    ],
  })
)

// ---- 静态资源（CSS/JS/字体）：CacheFirst ----
registerRoute(
  ({ request }) =>
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'font',
  new CacheFirst({
    cacheName: 'static-assets',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 200,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30天
      }),
    ],
  })
)

// ---- 图片资源：StaleWhileRevalidate ----
registerRoute(
  ({ request }) => request.destination === 'image',
  new StaleWhileRevalidate({
    cacheName: 'images-cache',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 7 * 24 * 60 * 60, // 7天
      }),
    ],
  })
)

// ---- 页面导航：NetworkFirst + 离线页面回退 ----
// 当导航请求在网络不可用时，返回友好的离线提示页面
registerRoute(
  ({ request }) => request.mode === 'navigate',
  new NetworkFirst({
    cacheName: 'navigation-cache',
    networkTimeoutSeconds: 5,
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      {
        // 自定义离线回退处理器
        handlerDidError: async () => {
          return new Response(offlinePageHTML, {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/html; charset=utf-8' },
          })
        },
      },
    ],
  })
)

// ---- CDN/第三方资源：StaleWhileRevalidate ----
registerRoute(
  ({ url }) =>
    url.origin === 'https://cdn.jsdelivr.net' ||
    url.origin === 'https://fonts.googleapis.com' ||
    url.origin === 'https://fonts.gstatic.com',
  new StaleWhileRevalidate({
    cacheName: 'cdn-cache',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 7 * 24 * 60 * 60, // 7天
      }),
    ],
  })
)

// ============ 离线页面回退 HTML ============
const offlinePageHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>智慧学伴 - 离线模式</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; background: #f5f7fa; color: #333;
    }
    .offline-container {
      text-align: center; padding: 40px; max-width: 480px;
    }
    .offline-icon {
      font-size: 80px; margin-bottom: 24px; opacity: 0.6;
    }
    .offline-title {
      font-size: 24px; font-weight: 600; margin-bottom: 12px; color: #1976D2;
    }
    .offline-desc {
      font-size: 16px; color: #666; line-height: 1.6; margin-bottom: 32px;
    }
    .retry-btn {
      display: inline-block; padding: 12px 32px;
      background: #1976D2; color: #fff; border: none; border-radius: 8px;
      font-size: 16px; cursor: pointer; text-decoration: none;
    }
    .retry-btn:hover { background: #1565C0; }
    .offline-tips {
      margin-top: 24px; font-size: 14px; color: #999;
    }
  </style>
</head>
<body>
  <div class="offline-container">
    <div class="offline-icon">📡</div>
    <h1 class="offline-title">网络不可用</h1>
    <p class="offline-desc">
      您当前处于离线状态，部分功能可能无法使用。<br/>
      已缓存的内容仍可正常访问。
    </p>
    <button class="retry-btn" onclick="window.location.reload()">重新连接</button>
    <p class="offline-tips">请检查您的网络连接后重试</p>
  </div>
</body>
</html>`

// ============ Background Sync：离线操作队列 ============
import { Queue } from 'workbox-background-sync'

/** 离线笔记保存同步队列 */
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
      } catch {
        // 同步失败，重新入队等待下次
        await queue.unshiftRequest(entry)
        return
      }
    }
  },
})

/** 离线通用操作队列（用于非笔记类 POST/PUT/DELETE 请求） */
const offlineActionQueue = new Queue('offline-action-sync', {
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
            type: 'OFFLINE_ACTION_SYNCED',
            payload: {
              url: entry.request.url,
              method: entry.request.method,
              timestamp: Date.now(),
            },
          })
        })
      } catch {
        await queue.unshiftRequest(entry)
        return
      }
    }
  },
})

// 拦截离线时的写操作请求
self.addEventListener('fetch', (event) => {
  const { request } = event
  const isWriteMethod = request.method === 'POST' || request.method === 'PUT' || request.method === 'DELETE'
  const isApiRequest = request.url.includes('/api/v1/')

  if (!isWriteMethod || !isApiRequest || navigator.onLine) {
    return
  }

  // 笔记相关请求走笔记专用队列
  if (request.url.includes('/api/v1/notes')) {
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

  // 其他 API 写操作走通用队列
  event.respondWith(
    offlineActionQueue.pushRequest({ request: event.request }).then(() => {
      return new Response(
        JSON.stringify({
          code: 202,
          message: '操作已暂存，将在网络恢复后同步',
          data: null,
        }),
        {
          status: 202,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    })
  )
})

// ============ Push Notification 支持 ============
self.addEventListener('push', (event) => {
  if (!event.data) return

  const data = event.data.json()
  const title = data.title || '智慧学伴通知'
  const options: NotificationOptions = {
    body: data.body || '',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
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

  const urlToOpen = (event.notification.data as { url?: string })?.url || '/'

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
    event.ports[0].postMessage({ version: '2.0.0' })
  }
})

// ============ 类型导出（确保 TypeScript 编译通过） ============
export {}
