/**
 * AI4Edu 认证 API
 */
import api from './api'

// ============ 类型定义 ============

export interface LoginParams {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user_id: number
  nickname: string
  role: string
  avatar_url: string | null
}

export interface RegisterParams {
  email: string
  password: string
  nickname: string
  role?: string
  school?: string
  grade?: string
}

export interface RegisterResponse {
  user_id: number
  email: string
  nickname: string
  access_token: string
  refresh_token: string
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  id: number
  email: string
  nickname: string
  avatar_url: string | null
  role: string
  grade: string | null
  school: string | null
  major?: string | null
  phone?: string | null
  bio?: string | null
  default_scene: string
  locale: string
  onboarding_completed: boolean
  tenant_id: number | null
  /** 服务端保存的偏好（theme / default_scene / sidebar_collapsed 等） */
  preferences?: Record<string, unknown> | null
  created_at: string
}

// ============ API 方法 ============

export const authApi = {
  /**
   * 用户登录
   * 注意：api 拦截器已将 {code,data,message} 解包，直接返回 data 字段内容
   */
  async login(params: LoginParams): Promise<LoginResponse> {
    // api 拦截器 return data 即 {code,data,...}，其中 .data 是业务数据
    const res = await api.post('/auth/login', params)
    return (res as any).data ?? res
  },

  /**
   * 用户注册
   */
  async register(params: RegisterParams): Promise<RegisterResponse> {
    const res = await api.post('/auth/register', params)
    return (res as any).data ?? res
  },

  /**
   * 刷新Token
   */
  async refresh(refreshToken: string): Promise<RefreshResponse> {
    const res = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return (res as any).data ?? res
  },

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<UserInfo> {
    const res = await api.get('/auth/me')
    return (res as any).data ?? res
  },

  /**
   * 登出
   */
  async logout(): Promise<void> {
    await api.post('/auth/logout')
  },

  /**
   * 完成 Onboarding 引导，持久化到后端
   * @param userId 用户ID
   * @param data 引导数据（角色、兴趣、目标）
   */
  async completeOnboarding(
    userId: number,
    data: { role: string; major: string; interests: string[]; goals: string[] },
  ): Promise<void> {
    await api.post(`/users/${userId}/onboarding`, data)
  },
}
