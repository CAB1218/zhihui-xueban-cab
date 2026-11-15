<template>
  <div
    class="upload-zone"
    :class="{ 'upload-zone--dragover': isDragOver }"
    @dragover.prevent="isDragOver = true"
    @dragleave.prevent="isDragOver = false"
    @drop.prevent="handleDrop"
    @click="triggerFileInput"
  >
    <input
      ref="fileInputRef"
      type="file"
      multiple
      class="upload-zone__input"
      @change="handleFileChange"
    />
    <div class="upload-zone__content">
      <el-icon :size="48" color="#1976D2"><UploadFilled /></el-icon>
      <p>将文件拖到此处，或点击上传</p>
      <p class="upload-zone__hint">支持 PDF、Word、PPT、图片等格式，单文件最大 50MB</p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 拖拽上传区域组件
 */
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'

const emit = defineEmits<{
  (e: 'files-selected', files: File[]): void
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)

function triggerFileInput(): void {
  fileInputRef.value?.click()
}

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    emit('files-selected', Array.from(input.files))
    input.value = ''
  }
}

function handleDrop(event: DragEvent): void {
  isDragOver.value = false
  if (event.dataTransfer?.files.length) {
    emit('files-selected', Array.from(event.dataTransfer.files))
  }
}
</script>

<style lang="scss" scoped>
.upload-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--border-radius-lg);
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover,
  &--dragover {
    border-color: var(--color-info);
    background: rgba(25, 118, 210, 0.04);
  }

  &__input {
    display: none;
  }

  &__content {
    p {
      margin: 8px 0 0;
      color: var(--color-text-secondary);
      font-size: 14px;
    }
  }

  &__hint {
    font-size: 12px !important;
    color: var(--color-text-placeholder) !important;
  }
}
</style>
