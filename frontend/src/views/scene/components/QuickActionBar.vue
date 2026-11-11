<template>
  <div class="quick-action-bar">
    <div class="quick-action-bar__header">
      <h3 class="quick-action-bar__title">{{ title }}</h3>
    </div>
    <div class="quick-action-bar__actions">
      <el-button
        v-for="action in actions"
        :key="action.label"
        :type="action.buttonType"
        :icon="undefined"
        plain
        class="quick-action-bar__btn"
        @click="handleAction(action)"
      >
        <el-icon class="quick-action-bar__btn-icon"><component :is="action.icon" /></el-icon>
        {{ action.label }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 快捷工具栏（跨场景共享组件）
 * 接收 QuickAction[] 列表，渲染按钮组
 * 点击按钮 emit action 事件，由父组件处理路由跳转
 */
import type { QuickAction } from '../types'

interface Props {
  /** 快捷操作列表 */
  actions: QuickAction[]
  /** 工具栏标题，默认"快捷工具" */
  title?: string
}

interface Emits {
  /** 点击操作时触发 */
  (e: 'action', action: QuickAction): void
}

withDefaults(defineProps<Props>(), {
  title: '快捷工具',
})

const emit = defineEmits<Emits>()

/** 处理按钮点击，向父组件 emit action 事件 */
function handleAction(action: QuickAction): void {
  emit('action', action)
}
</script>

<style lang="scss" scoped>
.quick-action-bar {
  padding: 16px;
  background: var(--el-bg-color, #fff);
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  &__header {
    margin-bottom: 12px;
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-primary, #303133);
    margin: 0;
  }

  &__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  &__btn {
    flex: 1;
    min-width: 120px;
    justify-content: center;
  }

  &__btn-icon {
    margin-right: 4px;
  }
}
</style>
