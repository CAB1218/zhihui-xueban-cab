<template>
  <div class="file-preview">
    <!-- 图片预览 -->
    <el-image
      v-if="isImage"
      :src="previewUrl"
      fit="contain"
      class="file-preview__image"
      :preview-src-list="[previewUrl]"
    />

    <!-- PDF / 文档 iframe 预览 -->
    <iframe
      v-else-if="isPdf"
      :src="previewUrl"
      class="file-preview__iframe"
      frameborder="0"
    />

    <!-- 代码 / 文本预览 -->
    <pre v-else-if="textContent" class="file-preview__text">{{ textContent }}</pre>

    <!-- 不支持预览 -->
    <div v-else class="file-preview__unsupported">
      <el-icon :size="48" color="#999"><Document /></el-icon>
      <p>该文件类型暂不支持在线预览</p>
      <el-button type="primary" @click="handleDownload">下载文件</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 文件预览组件
 */
import { computed } from 'vue'
import { Document } from '@element-plus/icons-vue'

const props = defineProps<{
  previewUrl: string
  resourceType: string
  mimeType?: string
  textContent?: string
}>()

const emit = defineEmits<{
  (e: 'download'): void
}>()

const isImage = computed(() => ['image'].includes(props.resourceType))
const isPdf = computed(() => props.resourceType === 'pdf')

function handleDownload(): void {
  emit('download')
}
</script>

<style lang="scss" scoped>
.file-preview {
  background: var(--color-bg-secondary);
  border-radius: var(--border-radius-md);
  overflow: hidden;

  &__image {
    width: 100%;
    max-height: 500px;
  }

  &__iframe {
    width: 100%;
    height: 600px;
    border: none;
  }

  &__text {
    padding: 16px;
    max-height: 500px;
    overflow: auto;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }

  &__unsupported {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 300px;
    gap: 12px;

    p {
      color: var(--color-text-secondary);
    }
  }
}
</style>
