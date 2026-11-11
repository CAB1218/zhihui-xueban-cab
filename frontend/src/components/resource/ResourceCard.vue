<template>
  <div class="resource-card" @click="$emit('click', resource)">
    <div class="resource-card__icon" :style="{ background: typeColor + '20', color: typeColor }">
      <el-icon :size="28"><component :is="typeIcon" /></el-icon>
    </div>
    <div class="resource-card__info">
      <h4 class="resource-card__title">{{ resource.title }}</h4>
      <div class="resource-card__meta">
        <el-tag size="small" :type="typeTagType">{{ resource.resource_type }}</el-tag>
        <span v-if="resource.file_size" class="resource-card__size">{{ formatSize(resource.file_size) }}</span>
      </div>
      <div v-if="resource.tags && resource.tags.length" class="resource-card__tags">
        <el-tag v-for="tag in resource.tags.slice(0, 3)" :key="tag" size="small" type="info" effect="plain">
          {{ tag }}
        </el-tag>
      </div>
      <span class="resource-card__time">{{ resource.created_at ? formatDate(resource.created_at) : '' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 资源卡片组件
 */
import { computed } from 'vue'
import type { ResourceItem } from '@/services/resource'

const props = defineProps<{
  resource: ResourceItem
}>()

defineEmits<{
  (e: 'click', resource: ResourceItem): void
}>()

const typeIconMap: Record<string, string> = {
  pdf: 'Document',
  docx: 'Document',
  pptx: 'Document',
  video: 'Film',
  audio: 'Headset',
  image: 'Picture',
}

const typeColorMap: Record<string, string> = {
  pdf: '#F44336',
  docx: '#1976D2',
  pptx: '#FF6F00',
  video: '#7B1FA2',
  audio: '#00796B',
  image: '#388E3C',
  other: '#757575',
}

const typeIcon = computed(() => typeIconMap[props.resource.resource_type] || 'Document')
const typeColor = computed(() => typeColorMap[props.resource.resource_type] || typeColorMap.other)
const typeTagType = computed(() => {
  const map: Record<string, string> = { pdf: 'danger', docx: '', pptx: 'warning', video: 'success', audio: 'info', image: 'success' }
  return map[props.resource.resource_type] || 'info'
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
.resource-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-md);
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
  }

  &__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    border-radius: var(--border-radius-md);
    flex-shrink: 0;
  }

  &__info {
    flex: 1;
    min-width: 0;
  }

  &__title {
    font-size: 15px;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }

  &__size {
    font-size: 12px;
    color: var(--color-text-secondary);
  }

  &__tags {
    display: flex;
    gap: 4px;
    margin-bottom: 4px;
    flex-wrap: wrap;
  }

  &__time {
    font-size: 12px;
    color: var(--color-text-placeholder);
  }
}
</style>
