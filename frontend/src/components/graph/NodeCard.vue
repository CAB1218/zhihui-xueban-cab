<template>
  <el-card
    shadow="hover"
    :class="['node-card', { 'node-card--selected': selected }]"
    @click="$emit('click', node)"
  >
    <div class="node-card__header">
      <span class="node-card__dot" :style="{ background: subjectColor }" />
      <span class="node-card__name">{{ node.name || node.id }}</span>
      <!-- Misconception 角标 -->
      <MisconceptionBadge
        v-if="node.has_misconception"
        :misconceptions="node.misconceptions || []"
        @open-dialog="$emit('open-misconception', node)"
      />
    </div>
    <p v-if="node.description" class="node-card__desc">{{ node.description }}</p>
    <div class="node-card__footer">
      <el-tag v-if="node.subject" size="small" type="info">{{ subjectName }}</el-tag>
    </div>
  </el-card>
</template>

<script setup lang="ts">
/**
 * AI4Edu 知识点卡片组件
 * 支持 misconception 角标展示，subject 中英文映射
 */
import { computed } from 'vue'
import MisconceptionBadge from './MisconceptionBadge.vue'
import type { Misconception } from '@/services/graph'

interface KnowledgeNode {
  id: string
  name?: string
  subject?: string
  description?: string
  has_misconception?: boolean
  misconceptions?: Misconception[]
  [key: string]: unknown
}

const props = defineProps<{
  node: KnowledgeNode
  selected?: boolean
}>()

defineEmits<{
  (e: 'click', node: KnowledgeNode): void
  (e: 'open-misconception', node: KnowledgeNode): void
}>()

const subjectColorMap: Record<string, string> = {
  math: '#1976D2',
  physics: '#F57C00',
  chemistry: '#4CAF50',
  biology: '#388E3C',
  cs: '#7B1FA2',
  chinese: '#D32F2F',
  english: '#00796B',
  history: '#5D4037',
  geography: '#0288D1',
  politics: '#C62828',
  pe: '#FF6F00',
  art: '#AD1457',
}

const subjectNameMap: Record<string, string> = {
  math: '数学',
  physics: '物理学',
  chemistry: '化学',
  biology: '生物学',
  cs: '计算机科学',
  chinese: '语文',
  english: '英语',
  history: '历史',
  geography: '地理',
  politics: '政治',
  pe: '体育',
  art: '艺术',
}

const subjectColor = computed(() => subjectColorMap[props.node.subject || ''] || '#5B8FF9')
const subjectName = computed(() => subjectNameMap[props.node.subject || ''] || props.node.subject || '')
</script>

<style lang="scss" scoped>
.node-card {
  cursor: pointer;
  transition: transform 0.15s ease;
  position: relative;

  &:hover {
    transform: translateY(-2px);
  }

  &--selected {
    background: #e4e7ed;
    border-color: #a8abb2;

    .node-card__dot { background: #909399 !important; }
    .node-card__name, .node-card__desc { color: #606266; }
  }

  &__header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    position: relative;
  }

  &__dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  &__name {
    font-weight: 600;
    font-size: 15px;
    color: var(--color-text-primary);
  }

  &__desc {
    font-size: 13px;
    color: var(--color-text-secondary);
    margin: 4px 0 8px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__footer {
    display: flex;
    gap: 6px;
  }
}
</style>
