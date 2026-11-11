<template>
  <div class="scene-welcome-banner">
    <!-- 左侧场景图标（P0 用 Element Plus 图标 + 主题色圆形背景） -->
    <div class="scene-welcome-banner__icon" :style="{ backgroundColor: config.color }">
      <el-icon :size="32" color="#FFFFFF">
        <component :is="config.illustration" />
      </el-icon>
    </div>

    <!-- 右侧场景信息 -->
    <div class="scene-welcome-banner__info">
      <h2 class="scene-welcome-banner__name">{{ config.name }}</h2>
      <p class="scene-welcome-banner__slogan">{{ config.slogan }}</p>
      <p class="scene-welcome-banner__description">{{ config.description }}</p>
    </div>

    <!-- 示例数据标签（接入真实数据后由父组件关掉） -->
    <el-tag v-if="demo" type="info" size="small" class="scene-welcome-banner__demo-tag">示例数据</el-tag>
  </div>
</template>

<script setup lang="ts">
/**
 * 场景欢迎横幅（跨场景共享组件）
 * 渲染场景图标、名称、slogan、描述
 * 背景使用 accentColor 的浅色渐变
 */
import type { SceneConfigEntry } from '@/utils/constants'

interface Props {
  /** 场景配置，从 SCENE_CONFIG[currentSceneType] 传入 */
  config: SceneConfigEntry
  /** 是否展示「示例数据」角标；接入真实数据后可传 false */
  demo?: boolean
}

withDefaults(defineProps<Props>(), {
  demo: true,
})
</script>

<style lang="scss" scoped>
.scene-welcome-banner {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg, 16px);
  padding: 16px 24px;
  margin-bottom: var(--spacing-lg, 16px);
  border-radius: 12px;
  background: linear-gradient(135deg, var(--scene-primary-bg, #E3F2FD) 0%, var(--scene-primary-bg-hover, #BBDEFB) 100%);
  position: relative;
  min-height: 100px;

  &__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__name {
    font-size: 22px;
    font-weight: 700;
    color: var(--color-text-primary, #303133);
    margin: 0 0 4px 0;
  }

  &__slogan {
    font-size: 14px;
    font-weight: 600;
    color: var(--scene-primary-color, #1976D2);
    margin: 0 0 2px 0;
  }

  &__description {
    font-size: 13px;
    color: var(--color-text-secondary, #909399);
    margin: 0;
  }

  &__demo-tag {
    position: absolute;
    top: 12px;
    right: 12px;
  }
}
</style>
