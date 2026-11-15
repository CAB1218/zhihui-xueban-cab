/**
 * 智慧学伴 场景 API
 */
import api from './api'
import { SceneType } from '@/utils/constants'

// ============ 类型定义 ============

export interface SceneConfig {
  scene_type: SceneType
  name: string
  name_en: string
  icon: string
  primary_color: string
  description: string | null
  layout_config: Record<string, unknown> | null
  feature_flags: Record<string, boolean> | null
  default_widgets: string[] | null
  ai_prompt_template: string | null
}

export interface SceneRecommendation {
  recommended_scene: SceneType
  reason: string
  confidence: number
  alternative_scenes: SceneType[] | null
}

export interface SceneSwitchResponse {
  scene_type: SceneType
  scene_name: string
  primary_color: string
  layout_config: Record<string, unknown> | null
  feature_flags: Record<string, boolean> | null
  widgets: string[] | null
}

// ============ API 方法 ============

export const sceneApi = {
  /**
   * 获取当前场景
   */
  async getCurrentScene(): Promise<SceneConfig> {
    const response = await api.get('/scenes/current')
    return response.data
  },

  /**
   * 切换场景
   */
  async switchScene(sceneType: SceneType, courseId?: number): Promise<SceneSwitchResponse> {
    const response = await api.post('/scenes/switch', {
      scene_type: sceneType,
      course_id: courseId,
    })
    return response.data
  },

  /**
   * 获取场景推荐
   */
  async getRecommendation(context?: string): Promise<SceneRecommendation> {
    const response = await api.get('/scenes/recommendation', {
      params: { context },
    })
    return response.data
  },

  /**
   * 获取指定场景配置
   */
  async getSceneConfig(sceneType: SceneType): Promise<SceneConfig> {
    const response = await api.get(`/scenes/${sceneType}/config`)
    return response.data
  },

  /**
   * 获取场景列表
   */
  async listScenes(): Promise<SceneConfig[]> {
    const response = await api.get('/scenes/list')
    return response.data
  },
}
