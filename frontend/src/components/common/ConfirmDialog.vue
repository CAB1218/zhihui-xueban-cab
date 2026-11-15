<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="closeOnClickModal"
    :close-on-press-escape="closeOnPressEscape"
    @close="handleClose"
  >
    <p class="confirm-dialog__message">{{ message }}</p>
    <template #footer>
      <el-button @click="handleCancel">{{ cancelText }}</el-button>
      <el-button :type="confirmType" @click="handleConfirm">{{ confirmText }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 确认对话框组件
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmType?: 'primary' | 'success' | 'warning' | 'danger'
  width?: string
  closeOnClickModal?: boolean
  closeOnPressEscape?: boolean
}>(), {
  title: '确认操作',
  confirmText: '确定',
  cancelText: '取消',
  confirmType: 'primary',
  width: '420px',
  closeOnClickModal: false,
  closeOnPressEscape: true,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
  cancel: []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val),
})

function handleConfirm(): void {
  emit('confirm')
  visible.value = false
}

function handleCancel(): void {
  emit('cancel')
  visible.value = false
}

function handleClose(): void {
  visible.value = false
}
</script>

<style lang="scss" scoped>
.confirm-dialog__message {
  font-size: 14px;
  color: var(--color-text-regular);
  line-height: 1.6;
}
</style>
