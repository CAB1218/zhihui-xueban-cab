<template>
  <div class="empty-state">
    <el-icon :size="64" class="empty-state__icon">
      <component :is="icon" />
    </el-icon>
    <h3 class="empty-state__title">{{ title }}</h3>
    <p v-if="description" class="empty-state__description">{{ description }}</p>
    <el-button
      v-if="actionText"
      type="primary"
      @click="$emit('action')"
    >
      {{ actionText }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 空状态组件
 */
defineProps<{
  icon?: string
  title: string
  description?: string
  actionText?: string
}>()

defineEmits<{
  action: []
}>()
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl) var(--spacing-lg);
  text-align: center;

  &__icon {
    color: var(--color-text-placeholder);
    margin-bottom: var(--spacing-md);
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  &__description {
    font-size: 14px;
    color: var(--color-text-placeholder);
    margin-bottom: var(--spacing-lg);
    max-width: 400px;
  }
}
</style>
