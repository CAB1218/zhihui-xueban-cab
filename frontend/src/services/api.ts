/**
 * AI4Edu Axios 实例
 * 请求拦截：Token注入
 * 响应拦截：401自动刷新、错误统一处理
 */
import axios, { type AxiosInstance, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// 创建 Axios 实例
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 是否正在刷新Token
let isRefreshing = false
// Avoid stacking one toast for every concurrent request rejected by the limiter.
let lastRateLimitNoticeAt = 0
// 重试请求队列
let retryQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

/**
 * 请求拦截器
 * - 自动注入 Bearer Token
 * - 注入 X-Tenant-ID
 */
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()

    // 注入 Token
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }

    // 注入租户ID
    if (authStore.user?.tenant_id) {
      config.headers['X-Tenant-ID'] = String(authStore.user.tenant_id)
    }

    // 注入请求ID（兼容 HTTP 环境）
    config.headers['X-Request-ID'] = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 * - 401 自动刷新 Token
 * - 错误统一 toast 提示
 */
api.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response

    // 统一响应格式处理
    if (data.code !== undefined && data.code !== 200 && data.code !== 0) {
      const errorMessage = data.message || '请求失败'
      ElMessage.error(errorMessage)
      return Promise.reject(new Error(errorMessage))
    }

    return data
  },
  async (error) => {
    const { response } = error

    if (!response) {
      ElMessage.error('网络连接异常，请检查网络设置')
      return Promise.reject(error)
    }

    const { status, data } = response

    // 允许调用方用 config.silent 关闭自动 toast：
    // 例如「该课程暂无学情记录」这类 404 属于正常空态，应由页面渲染空状态而不是弹错误
    const silent = (error.config as { silent?: boolean } | undefined)?.silent === true
    if (silent) {
      return Promise.reject(error)
    }

    switch (status) {
      case 401: {
        const authStore = useAuthStore()

        // Token 过期，尝试刷新（已在 retry 请求中则跳过，避免无限循环）
        if (error.config?._retry) {
          // 已重试过的请求直接清除认证，跳转登录
          authStore.clearAuth()
          await router.push({ name: 'Login' })
          ElMessage.error('登录已过期，请重新登录')
          break
        }

        if (!isRefreshing && authStore.refreshToken) {
          isRefreshing = true

          try {
            await authStore.refreshAccessToken()
            const newToken = authStore.accessToken!

            // 重试所有排队的请求
            retryQueue.forEach(({ resolve }) => resolve(newToken))
            retryQueue = []

            // 重试当前请求（标记 _retry 防止递归）
            if (error.config) {
              error.config.headers.Authorization = `Bearer ${newToken}`
              error.config._retry = true
              return api.request(error.config)
            }
          } catch (refreshError) {
            // 刷新失败，清除认证状态
            retryQueue.forEach(({ reject }) => reject(refreshError))
            retryQueue = []
            authStore.clearAuth()
            await router.push({ name: 'Login' })
            ElMessage.error('登录已过期，请重新登录')
          } finally {
            isRefreshing = false
          }
        } else if (isRefreshing) {
          // 正在刷新中，将请求加入队列
          return new Promise((resolve, reject) => {
            retryQueue.push({
              resolve: (token: string) => {
                if (error.config) {
                  error.config.headers.Authorization = `Bearer ${token}`
                  error.config._retry = true
                  resolve(api.request(error.config))
                }
              },
              reject,
            })
          })
        } else {
          // 没有 refreshToken，直接清除并跳转登录
          authStore.clearAuth()
          await router.push({ name: 'Login' })
        }
        break
      }
      case 403:
        ElMessage.error(data.message || '权限不足')
        break
      case 404:
        ElMessage.error(data.message || '请求的资源不存在')
        break
      case 422:
        ElMessage.error(data.message || '数据校验失败')
        break
      case 429:
        if (Date.now() - lastRateLimitNoticeAt > 3000) {
          lastRateLimitNoticeAt = Date.now()
          ElMessage.warning({
            message: '请求过于频繁，请稍后再试',
            grouping: true,
          })
        }
        break
      case 500:
        // 后端 AppException 会带 message，优先展示，便于定位而不是只说「服务器内部错误」
        ElMessage.error(data?.message || '服务器内部错误')
        break
      case 503:
        ElMessage.error(data?.message || '服务暂时不可用，请稍后再试')
        break
      default:
        ElMessage.error(data.message || '请求失败')
    }

    return Promise.reject(error)
  }
)

export default api
