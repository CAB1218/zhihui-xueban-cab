/**
 * 智慧学伴 性能监控组合式函数
 * 提供组件级别的性能追踪能力
 */
import { ref, onMounted, onUnmounted } from 'vue'
import {
  startSpan,
  endSpan,
  measureAsync,
  reportUserAction,
  reportPageView,
} from '@/utils/telemetry'

export interface PerformanceMetrics {
  /** 页面加载时间(ms) */
  pageLoadTime: number
  /** API 平均响应时间(ms) */
  avgApiResponseTime: number
  /** 渲染时间(ms) */
  renderTime: number
  /** 内存使用量(MB) */
  memoryUsage: number
}

export function usePerformance(componentName?: string) {
  const isLoading = ref(false)
  const lastRenderTime = ref(0)
  const apiCallCount = ref(0)

  // 性能追踪 span 前缀
  const spanPrefix = componentName ? `${componentName}:` : ''

  /**
   * 追踪组件渲染时间
   */
  function trackRender(): void {
    const spanName = `${spanPrefix}render`
    startSpan(spanName)
    // 使用 nextTick 或 requestAnimationFrame 标记渲染完成
    requestAnimationFrame(() => {
      endSpan(spanName)
      lastRenderTime.value = performance.now()
    })
  }

  /**
   * 追踪 API 请求
   */
  async function trackApiCall<T>(
    name: string,
    fn: () => Promise<T>,
  ): Promise<T> {
    isLoading.value = true
    apiCallCount.value++

    const spanName = `${spanPrefix}api:${name}`
    try {
      const result = await measureAsync(spanName, fn)
      return result
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 追踪用户交互
   */
  function trackAction(
    action: string,
    label?: string,
    value?: number,
  ): void {
    reportUserAction(action, componentName || 'unknown', label, value)
  }

  /**
   * 追踪页面浏览（在路由切换时调用）
   */
  function trackPageView(path?: string, title?: string): void {
    reportPageView(path, title)
  }

  /**
   * 获取当前性能指标
   */
  function getMetrics(): PerformanceMetrics {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined

    return {
      pageLoadTime: navigation
        ? Math.round(navigation.loadEventEnd - navigation.startTime)
        : 0,
      avgApiResponseTime: 0, // 由 API 拦截器累计
      renderTime: lastRenderTime.value
        ? Math.round(lastRenderTime.value - (navigation?.startTime ?? 0))
        : 0,
      memoryUsage: getMemoryUsage(),
    }
  }

  // 组件挂载时自动追踪渲染
  onMounted(() => {
    if (componentName) {
      trackRender()
    }
  })

  // 组件卸载时记录
  onUnmounted(() => {
    if (componentName) {
      endSpan(`${spanPrefix}lifecycle`)
    }
  })

  return {
    isLoading,
    lastRenderTime,
    apiCallCount,
    trackRender,
    trackApiCall,
    trackAction,
    trackPageView,
    getMetrics,
  }
}

/**
 * 获取浏览器内存使用量（仅 Chrome 支持）
 */
function getMemoryUsage(): number {
  const performance = window.performance as any
  if (performance?.memory?.usedJSHeapSize) {
    return Math.round(performance.memory.usedJSHeapSize / 1024 / 1024)
  }
  return 0
}
