/**
 * AI4Edu 前端遥测工具
 * 集成 Web Vitals、错误追踪、性能监控
 */

// ============ 配置 ============

const TELEMETRY_ENDPOINT = '/api/v1/telemetry'
const ENABLED = import.meta.env.PROD

// ============ Web Vitals ============

export interface WebVitalMetric {
  name: string
  value: number
  rating: 'good' | 'needs-improvement' | 'poor'
  delta: number
  navigationType: string
  timestamp: number
}

/**
 * 初始化 Web Vitals 监控
 * web-vitals v5：onFID 已被 INP 取代；各回调使用库自带的 Metric 类型
 */
export async function initWebVitals(): Promise<void> {
  if (!ENABLED) return

  try {
    const { onLCP, onCLS, onFCP, onTTFB, onINP } = await import('web-vitals')
    type WebVitalLibMetric = import('web-vitals').Metric

    const reportMetric = (metric: WebVitalLibMetric): void => {
      reportToBackend('web_vital', {
        name: metric.name,
        value: Math.round(metric.value),
        rating: metric.rating,
        delta: Math.round(metric.delta),
        navigationType: metric.navigationType,
      })
    }

    onLCP(reportMetric)
    onCLS(reportMetric)
    onFCP(reportMetric)
    onTTFB(reportMetric)
    onINP(reportMetric)
  } catch (error) {
    console.warn('[Telemetry] web-vitals not available:', error)
  }
}

// ============ 错误追踪 ============

export interface ErrorEvent {
  type: 'js_error' | 'vue_error' | 'resource_error' | 'promise_error' | 'api_error'
  message: string
  stack?: string
  filename?: string
  lineno?: number
  colno?: number
  url?: string
  timestamp: number
}

/**
 * 初始化全局错误捕获
 */
export function initErrorTracking(): void {
  // JS 运行时错误
  window.addEventListener('error', (event) => {
    const errorEvent: ErrorEvent = {
      type: event.target instanceof HTMLElement ? 'resource_error' : 'js_error',
      message: event.message || 'Unknown error',
      stack: event.error?.stack,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      url: window.location.href,
      timestamp: Date.now(),
    }

    if (event.target instanceof HTMLElement) {
      errorEvent.message = `Resource failed to load: ${(event.target as HTMLElement).tagName}`
      const src = (event.target as HTMLElement).getAttribute('src') ||
                  (event.target as HTMLElement).getAttribute('href')
      if (src) errorEvent.filename = src
    }

    reportToBackend('error', errorEvent)
  })

  // 未处理的 Promise 拒绝
  window.addEventListener('unhandledrejection', (event) => {
    const errorEvent: ErrorEvent = {
      type: 'promise_error',
      message: event.reason?.message || String(event.reason),
      stack: event.reason?.stack,
      url: window.location.href,
      timestamp: Date.now(),
    }
    reportToBackend('error', errorEvent)
  })
}

/**
 * 手动上报 Vue 组件错误
 */
export function reportVueError(err: Error, _vm: any, info: string): void {
  const errorEvent: ErrorEvent = {
    type: 'vue_error',
    message: err.message,
    stack: err.stack,
    filename: info,
    url: window.location.href,
    timestamp: Date.now(),
  }
  reportToBackend('error', errorEvent)
}

/**
 * 上报 API 请求错误
 */
export function reportApiError(
  method: string,
  url: string,
  status: number,
  message: string,
): void {
  const errorEvent: ErrorEvent = {
    type: 'api_error',
    message: `API ${method} ${url} failed: ${status} - ${message}`,
    url: window.location.href,
    timestamp: Date.now(),
  }
  reportToBackend('error', errorEvent)
}

// ============ 页面浏览追踪 ============

export interface PageViewEvent {
  path: string
  title: string
  referrer: string
  timestamp: number
}

let lastPageViewTime = 0

/**
 * 上报页面浏览
 */
export function reportPageView(path?: string, title?: string): void {
  if (!ENABLED) return

  const now = Date.now()
  // 防抖：1秒内不重复上报
  if (now - lastPageViewTime < 1000) return
  lastPageViewTime = now

  const event: PageViewEvent = {
    path: path || window.location.pathname,
    title: title || document.title,
    referrer: document.referrer,
    timestamp: now,
  }
  reportToBackend('page_view', event)
}

// ============ 用户行为追踪 ============

export interface UserActionEvent {
  action: string
  category: string
  label?: string
  value?: number
  timestamp: number
}

/**
 * 上报用户行为（如按钮点击、场景切换）
 */
export function reportUserAction(
  action: string,
  category: string,
  label?: string,
  value?: number,
): void {
  if (!ENABLED) return

  const event: UserActionEvent = {
    action,
    category,
    label,
    value,
    timestamp: Date.now(),
  }
  reportToBackend('user_action', event)
}

// ============ 性能追踪 ============

export interface PerformanceSpan {
  name: string
  duration: number
  attributes?: Record<string, string | number>
  timestamp: number
}

const activeSpans = new Map<string, number>()

/**
 * 开始一个性能追踪 span
 */
export function startSpan(name: string): void {
  activeSpans.set(name, performance.now())
}

/**
 * 结束一个性能追踪 span 并上报
 */
export function endSpan(
  name: string,
  attributes?: Record<string, string | number>,
): void {
  const startTime = activeSpans.get(name)
  if (!startTime) return

  const duration = performance.now() - startTime
  activeSpans.delete(name)

  const span: PerformanceSpan = {
    name,
    duration: Math.round(duration),
    attributes,
    timestamp: Date.now(),
  }

  if (ENABLED) {
    reportToBackend('performance', span)
  }
}

/**
 * 测量一个异步操作的耗时
 */
export async function measureAsync<T>(
  name: string,
  fn: () => Promise<T>,
  attributes?: Record<string, string | number>,
): Promise<T> {
  startSpan(name)
  try {
    const result = await fn()
    endSpan(name, attributes)
    return result
  } catch (error) {
    endSpan(name, { ...attributes, error: 'true' })
    throw error
  }
}

// ============ API 请求拦截 ============

/**
 * 包装 fetch 请求，自动追踪响应时间和错误
 */
export function createTracedFetch(): typeof fetch {
  const originalFetch = window.fetch

  const tracedFetch: typeof fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input)
    const method = init?.method || 'GET'
    const spanName = `fetch:${method} ${url}`

    startSpan(spanName)

    try {
      const response = await originalFetch(input, init)
      endSpan(spanName, {
        status: response.status,
        method,
      })

      // 4xx/5xx 错误上报
      if (response.status >= 400) {
        reportApiError(method, url, response.status, response.statusText)
      }

      return response
    } catch (error) {
      endSpan(spanName, { error: 'true', method })
      reportApiError(method, url, 0, (error as Error).message)
      throw error
    }
  }

  return tracedFetch
}

// ============ 数据上报 ============

// 批量上报队列
const reportQueue: Array<{ type: string; payload: unknown }> = []
let reportTimer: ReturnType<typeof setTimeout> | null = null

/**
 * 上报事件到后端
 */
function reportToBackend(type: string, payload: unknown): void {
  reportQueue.push({ type, payload })

  // 批量上报：每5秒或累积10条时上报
  if (reportQueue.length >= 10) {
    flushReports()
  } else if (!reportTimer) {
    reportTimer = setTimeout(flushReports, 5000)
  }
}

/**
 * 刷新上报队列
 */
function flushReports(): void {
  if (reportTimer) {
    clearTimeout(reportTimer)
    reportTimer = null
  }

  if (reportQueue.length === 0) return

  const batch = reportQueue.splice(0, reportQueue.length)

  // 使用 sendBeacon 优先，确保页面卸载时也能上报
  const data = JSON.stringify({
    events: batch,
    sessionId: getSessionId(),
    userAgent: navigator.userAgent,
    url: window.location.href,
  })

  if (navigator.sendBeacon) {
    const blob = new Blob([data], { type: 'application/json' })
    navigator.sendBeacon(TELEMETRY_ENDPOINT, blob)
  } else {
    // 降级使用 fetch
    fetch(TELEMETRY_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: data,
      keepalive: true,
    }).catch(() => {
      // 上报失败静默处理，不影响用户体验
    })
  }
}

// ============ 会话管理 ============

const SESSION_KEY = 'ai4edu_session_id'

function getSessionId(): string {
  let sessionId = sessionStorage.getItem(SESSION_KEY)
  if (!sessionId) {
    sessionId = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
    sessionStorage.setItem(SESSION_KEY, sessionId)
  }
  return sessionId
}

// ============ 初始化 ============

/**
 * 初始化前端遥测系统
 */
export function initTelemetry(): void {
  if (!ENABLED) {
    console.info('[Telemetry] Telemetry disabled in development mode')
    return
  }

  initWebVitals()
  initErrorTracking()

  // 页面卸载前刷新队列
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      flushReports()
    }
  })

  // 页面离开前刷新
  window.addEventListener('pagehide', flushReports)

  console.info('[Telemetry] Telemetry initialized')
}

// 导出 flush 用于手动刷新
export { flushReports }
