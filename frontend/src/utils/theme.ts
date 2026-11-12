/**
 * 主题工具
 * 偏好设置里的「浅色 / 深色 / 跟随系统」统一走这里：
 * - html 上挂 `dark` 类，交给 element-plus 的 dark css-vars 与 dark.scss 生效
 * - auto 时监听系统配色变化，改动后即时生效
 */
export type ThemeMode = 'light' | 'dark' | 'auto'

const MEDIA = '(prefers-color-scheme: dark)'

export function resolveDark(theme: ThemeMode): boolean {
  if (theme === 'auto') {
    return typeof window !== 'undefined' && window.matchMedia(MEDIA).matches
  }
  return theme === 'dark'
}

export function applyTheme(theme: ThemeMode): void {
  if (typeof document === 'undefined') return
  const dark = resolveDark(theme)
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
}

let mediaBound = false

/** auto 模式下跟随系统切换；重复调用只绑定一次 */
export function watchSystemTheme(getTheme: () => ThemeMode): void {
  if (mediaBound || typeof window === 'undefined') return
  mediaBound = true
  const mql = window.matchMedia(MEDIA)
  const handler = (): void => {
    if (getTheme() === 'auto') applyTheme('auto')
  }
  if (mql.addEventListener) mql.addEventListener('change', handler)
  else if ((mql as any).addListener) (mql as any).addListener(handler)
}

/** 从本地缓存里读主题（应用启动时用，避免闪白） */
export function readStoredTheme(): ThemeMode {
  try {
    const prefs = JSON.parse(localStorage.getItem('user_preferences') || '{}')
    const theme = prefs?.theme
    return theme === 'dark' || theme === 'auto' ? theme : 'light'
  } catch {
    return 'light'
  }
}
