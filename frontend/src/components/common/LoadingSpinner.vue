<template>
  <div :class="['loading-spinner', `loading-spinner--${size}`]">
    <div class="loading-spinner__dot" />
    <div class="loading-spinner__dot" />
    <div class="loading-spinner__dot" />
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 加载动画组件
 */
defineProps<{
  size?: 'small' | 'medium' | 'large'
}>()
</script>

<style lang="scss" scoped>
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;

  &--small {
    .loading-spinner__dot {
      width: 6px;
      height: 6px;
    }
  }

  &--medium {
    .loading-spinner__dot {
      width: 10px;
      height: 10px;
    }
  }

  &--large {
    .loading-spinner__dot {
      width: 14px;
      height: 14px;
    }
  }

  &__dot {
    border-radius: 50%;
    background-color: var(--scene-primary-color, #1976D2);
    animation: bounce 1.4s infinite ease-in-out both;

    &:nth-child(1) {
      animation-delay: -0.32s;
    }

    &:nth-child(2) {
      animation-delay: -0.16s;
    }

    &:nth-child(3) {
      animation-delay: 0s;
    }
  }
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}
</style>
