<template>
  <div v-if="citations.length > 0" class="citation-list">
    <div class="citation-list__header">
      <el-icon :size="14"><Link /></el-icon>
      <span>引用来源</span>
    </div>
    <div class="citation-list__items">
      <div
        v-for="(citation, index) in citations"
        :key="index"
        class="citation-list__item"
        @click="handleClick(citation)"
      >
        <span class="citation-list__icon">{{ getCitationIcon(citation.type) }}</span>
        <el-tag :type="getCitationTagType(citation.type)" size="small" effect="plain">
          {{ getCitationTypeLabel(citation.type) }}
        </el-tag>
        <span class="citation-list__title">{{ citation.title }}</span>
        <span v-if="citation.teacher_name" class="citation-list__teacher">
          ({{ citation.teacher_name }}老师)
        </span>
        <el-icon :size="12" class="citation-list__arrow"><Right /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 引用来源列表组件
 * 展示 AI 回答引用的笔记/资源/老师方法/图谱节点
 * 点击可跳转到对应资源详情页
 */
import { useRouter } from 'vue-router'
import { Link, Right } from '@element-plus/icons-vue'
import type { Citation } from '@/services/agent'

defineProps<{
  citations: Citation[]
}>()

const router = useRouter()

/** 点击引用跳转 */
function handleClick(citation: Citation): void {
  if (!citation.source_url || citation.source_url === '#') return
  // 从 source_url 中提取路由路径
  const path = citation.source_url
  if (path.startsWith('/notes/')) {
    const noteId = path.replace('/notes/', '')
    router.push({ name: 'SceneNote', params: { id: noteId } })
  } else if (path.startsWith('/resources/')) {
    const resourceId = path.replace('/resources/', '')
    router.push({ name: 'ResourceDetail', params: { id: resourceId } })
  } else if (path.startsWith('/graph/nodes/')) {
    // 图谱节点跳转
    router.push({ name: 'GraphSquare' })
  } else if (path.startsWith('/')) {
    router.push(path)
  }
}

/** 获取引用类型图标 */
function getCitationIcon(type: string): string {
  const iconMap: Record<string, string> = {
    note: '📝',
    resource: '📄',
    teacher_method: '👨‍🏫',
    graph_node: '🕸️',
  }
  return iconMap[type] || '📎'
}

/** 获取引用类型标签 */
function getCitationTypeLabel(type: string): string {
  const labelMap: Record<string, string> = {
    note: '笔记',
    resource: '资源',
    teacher_method: '老师方法',
    graph_node: '图谱',
  }
  return labelMap[type] || '来源'
}

/** 获取引用类型标签样式 */
function getCitationTagType(type: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const typeMap: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    note: 'info',
    resource: 'primary',
    teacher_method: 'warning',
    graph_node: 'success',
  }
  return typeMap[type] || 'info'
}
</script>

<style lang="scss" scoped>
.citation-list {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;

  &__header {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #888;
    margin-bottom: 8px;
  }

  &__items {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  &__item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: #e3f2fd;
    }
  }

  &__icon {
    font-size: 14px;
  }

  &__title {
    font-size: 13px;
    color: #555;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__teacher {
    font-size: 12px;
    color: #999;
  }

  &__arrow {
    color: #ccc;
    flex-shrink: 0;
  }
}
</style>
