<template>
  <div class="tag-editor">
    <div class="tag-editor__tags">
      <el-tag
        v-for="tag in modelValue"
        :key="tag"
        closable
        size="default"
        @close="removeTag(tag)"
      >
        {{ tag }}
      </el-tag>
    </div>
    <div class="tag-editor__input">
      <el-input
        v-model="newTag"
        size="small"
        placeholder="添加标签"
        @keyup.enter="addTag"
      >
        <template #append>
          <el-button @click="addTag">添加</el-button>
        </template>
      </el-input>
    </div>
    <el-button size="small" type="primary" plain :loading="aiLoading" @click="autoTag">
      AI 自动标签
    </el-button>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 标签编辑器组件
 */
import { ref } from 'vue'

const props = defineProps<{
  modelValue: string[]
  resourceId?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', tags: string[]): void
  (e: 'auto-tag'): void
}>()

const newTag = ref('')
const aiLoading = ref(false)

function addTag(): void {
  const tag = newTag.value.trim()
  if (tag && !props.modelValue.includes(tag)) {
    emit('update:modelValue', [...props.modelValue, tag])
  }
  newTag.value = ''
}

function removeTag(tag: string): void {
  emit('update:modelValue', props.modelValue.filter((t) => t !== tag))
}

async function autoTag(): Promise<void> {
  aiLoading.value = true
  try {
    emit('auto-tag')
  } finally {
    aiLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
.tag-editor {
  &__tags {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }

  &__input {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;

    .el-input {
      width: 200px;
    }
  }
}
</style>
