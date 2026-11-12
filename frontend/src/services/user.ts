/**
 * 用户设置相关接口
 * 个人资料（/users/{id}）、密码（/users/{id}/password）、偏好（/users/{id}/preferences）
 */
import api from './api'
import type { UserInfo } from './auth'

export interface ProfilePayload {
  nickname?: string
  avatar_url?: string | null
  phone?: string | null
  grade?: string | null
  school?: string | null
  major?: string | null
  bio?: string | null
}

export interface PreferencePayload {
  theme?: 'light' | 'dark' | 'auto'
  locale?: string
  default_scene?: string
  sidebar_collapsed?: boolean
  show_buddy?: boolean
  notification_enabled?: boolean
}

export const userApi = {
  /** 用户详情（含手机号、简介等 auth/me 未返回的字段） */
  async getProfile(userId: number): Promise<UserInfo & { phone?: string | null; bio?: string | null }> {
    const res: any = await api.get(`/users/${userId}`)
    return (res?.data ?? res) as UserInfo & { phone?: string | null; bio?: string | null }
  },

  /** 更新个人资料（仅本人或管理员） */
  async updateProfile(userId: number, payload: ProfilePayload): Promise<UserInfo> {
    const res: any = await api.put(`/users/${userId}`, payload)
    return (res?.data ?? res) as UserInfo
  },

  /** 修改密码：需要旧密码 */
  async changePassword(userId: number, oldPassword: string, newPassword: string): Promise<void> {
    await api.put(`/users/${userId}/password`, {
      old_password: oldPassword,
      new_password: newPassword,
    })
  },

  /** 更新偏好设置（主题 / 默认场景 / 侧边栏等） */
  async updatePreferences(userId: number, payload: PreferencePayload): Promise<UserInfo> {
    const res: any = await api.put(`/users/${userId}/preferences`, payload)
    return (res?.data ?? res) as UserInfo
  },
}
