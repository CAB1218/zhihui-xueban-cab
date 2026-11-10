/**
 * AI4Edu 场景 Store
 * 管理当前场景、推荐、配置、主题应用
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sceneApi } from '@/services/scene'
import type { SceneConfig, SceneRecommendation } from '@/services/scene'
import { SceneType } from '@/utils/constants'

export const useSceneStore = defineStore('scene', () => {
  // ============ State ============

  /** 当前场景类型 */
  const currentSceneType = ref<SceneType>(
    (localStorage.getItem('current_scene') as SceneType) || SceneType.CLASSROOM
  )
  /** 当前场景配置 */
  const currentSceneConfig = ref<SceneConfig | null>(null)
  /** 场景推荐 */
  const recommendation = ref<SceneRecommendation | null>(null)
  /** 所有场景列表 */
  const sceneList = ref<SceneConfig[]>([])
  /** 加载状态 */
  const loading = ref<boolean>(false)

  // ============ Getters ============

  /** 当前场景主题色 */
  const primaryColor = computed<string>(() => {
    return currentSceneConfig.value?.primary_color ?? '#1976D2'
  })

  /** 当前场景名称 */
  const sceneName = computed<string>(() => {
    return currentSceneConfig.value?.name ?? '课堂模式'
  })

  /** 场景CSS类名 */
  const sceneClass = computed<string>(() => {
    return `scene-${currentSceneType.value}`
  })

  /** 当前场景功能开关 */
  const featureFlags = computed<Record<string, boolean>>(() => {
    return currentSceneConfig.value?.feature_flags ?? {}
  })

  /** 当前场景组件列表 */
  const widgets = computed<string[]>(() => {
    return currentSceneConfig.value?.default_widgets ?? []
  })

  /** 当前场景布局配置 */
  const layoutConfig = computed<Record<string, unknown>>(() => {
    return currentSceneConfig.value?.layout_config ?? {}
  })

  // ============ Actions ============

  /**
   * 切换场景
   * @param sceneType 目标场景类型
   */
  async function switchScene(sceneType: SceneType): Promise<void> {
    loading.value = true
    try {
      const response = await sceneApi.switchScene(sceneType)
      currentSceneType.value = sceneType
      currentSceneConfig.value = {
        ...currentSceneConfig.value,
        scene_type: response.scene_type,
        name: response.scene_name,
        primary_color: response.primary_color,
        layout_config: response.layout_config,
        feature_flags: response.feature_flags,
        default_widgets: response.widgets,
      } as SceneConfig
      localStorage.setItem('current_scene', sceneType)

      // 应用主题
      applySceneTheme(response.primary_color)
    } catch (error) {
      console.error('场景切换失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 应用场景主题到 DOM
   * @param color 主题色
   */
  function applySceneTheme(color?: string): void {
    const themeColor = color || primaryColor.value
    const root = document.documentElement

    // 主色
    root.style.setProperty('--scene-primary-color', themeColor)

    // 派生色
    root.style.setProperty('--scene-primary-light', `${themeColor}20`)
    root.style.setProperty('--scene-primary-dark', adjustColor(themeColor, -20))

    // 侧边栏渐变
    const gradients: Record<string, string> = {
      classroom: 'linear-gradient(180deg, #0d47a1 0%, #1565c0 100%)',
      self_study: 'linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%)',
      exam: 'linear-gradient(180deg, #e65100 0%, #ef6c00 100%)',
      discussion: 'linear-gradient(180deg, #4a148c 0%, #6a1b9a 100%)',
    }
    const sidebarBg = gradients[currentSceneType.value] || gradients.classroom
    root.style.setProperty('--scene-sidebar-gradient', sidebarBg)

    // Header 底部边框色
    root.style.setProperty('--scene-header-border', themeColor)
  }

  /**
   * 获取场景推荐
   * @param context 上下文信息
   */
  async function getRecommendation(context?: string): Promise<void> {
    try {
      const result = await sceneApi.getRecommendation(context)
      recommendation.value = result
    } catch (error) {
      console.error('获取场景推荐失败:', error)
    }
  }

  /**
   * 获取当前场景配置
   */
  async function fetchCurrentScene(): Promise<void> {
    try {
      const config = await sceneApi.getCurrentScene()
      currentSceneConfig.value = config
      currentSceneType.value = (config.scene_type as SceneType) || currentSceneType.value
      applySceneTheme(config.primary_color)
    } catch (error) {
      console.error('获取场景配置失败:', error)
    }
  }

  /**
   * 获取所有场景列表
   */
  async function fetchSceneList(): Promise<void> {
    try {
      const list = await sceneApi.listScenes()
      sceneList.value = list
    } catch (error) {
      console.error('获取场景列表失败:', error)
    }
  }

  /**
   * 获取指定场景配置
   * @param sceneType 场景类型
   */
  async function fetchSceneConfig(sceneType: SceneType): Promise<SceneConfig> {
    const config = await sceneApi.getSceneConfig(sceneType)
    return config
  }

  /**
   * 调整颜色亮度
   */
  function adjustColor(hex: string, amount: number): string {
    const num = parseInt(hex.replace('#', ''), 16)
    const r = Math.min(255, Math.max(0, ((num >> 16) & 0xFF) + amount))
    const g = Math.min(255, Math.max(0, ((num >> 8) & 0xFF) + amount))
    const b = Math.min(255, Math.max(0, (num & 0xFF) + amount))
    return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`
  }

  return {
    // State
    currentSceneType,
    currentSceneConfig,
    recommendation,
    sceneList,
    loading,
    // Getters
    primaryColor,
    sceneName,
    sceneClass,
    featureFlags,
    widgets,
    layoutConfig,
    // Actions
    switchScene,
    applySceneTheme,
    getRecommendation,
    fetchCurrentScene,
    fetchSceneList,
    fetchSceneConfig,
  }
})
