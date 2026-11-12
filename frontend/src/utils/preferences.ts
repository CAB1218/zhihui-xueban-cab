/**
 * 偏好设置：服务端字段与本地 store 之间的映射
 * 服务端存的是 snake_case JSON（users.preferences），本地 store 用 camelCase。
 */
import { useUserStore, type UserPreferences } from '@/stores/user'
import { applyTheme } from '@/utils/theme'

/** 默认进入场景可选项（与场景路由 /scene/:sceneType 对应） */
export const SCENE_OPTIONS = [
  { value: 'classroom', label: '课堂模式' },
  { value: 'self-study', label: '自习模式' },
  { value: 'exam', label: '考前模式' },
  { value: 'discussion', label: '讨论模式' },
] as const

const SERVER_KEYS: Record<string, keyof UserPreferences> = {
  theme: 'theme',
  locale: 'locale',
  default_scene: 'defaultScene',
  sidebar_collapsed: 'sidebarCollapsed',
  show_buddy: 'showBuddy',
  notification_enabled: 'notificationEnabled',
  font_size: 'fontSize',
}

/** 本地偏好 → 服务端 payload */
export function toServerPayload(prefs: UserPreferences): Record<string, unknown> {
  return {
    theme: prefs.theme,
    locale: prefs.locale,
    default_scene: prefs.defaultScene,
    sidebar_collapsed: prefs.sidebarCollapsed,
    show_buddy: prefs.showBuddy,
    notification_enabled: prefs.notificationEnabled,
  }
}

/** 登录/刷新用户信息后，用服务端偏好覆盖本地（服务端为空则保留本地） */
export function syncPreferencesFromServer(raw?: Record<string, unknown> | null): void {
  const userStore = useUserStore()
  if (raw && typeof raw === 'object') {
    const patch: Partial<UserPreferences> = {}
    for (const [serverKey, localKey] of Object.entries(SERVER_KEYS)) {
      const value = raw[serverKey]
      if (value === undefined || value === null) continue
      ;(patch as Record<string, unknown>)[localKey] = value
    }
    if (Object.keys(patch).length) userStore.updatePreferences(patch)
  }
  applyTheme(userStore.preferences.theme)
}
