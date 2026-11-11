<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="720px"
    :close-on-click-modal="false"
    class="file-import"
    @update:model-value="close"
    @closed="reset"
  >
    <div class="file-import__body">
      <!-- 使用说明 -->
      <ol class="file-import__steps">
        <li v-for="(s, i) in steps" :key="i">
          <span class="num">{{ i + 1 }}</span>
          <span>{{ s }}</span>
        </li>
      </ol>

      <div class="file-import__toolbar">
        <el-button :icon="Download" plain @click="handleDownload">下载导入模板</el-button>
        <el-button v-if="fieldRows.length" link type="primary" @click="showFormat = !showFormat">
          {{ showFormat ? '收起字段说明' : '查看字段说明' }}
        </el-button>
        <span class="file-import__accept">{{ acceptText }}</span>
      </div>

      <el-collapse-transition>
        <div v-show="showFormat && fieldRows.length" class="file-import__format">
          <el-table :data="fieldRows" size="small" border>
            <el-table-column prop="field" label="列名" width="120" />
            <el-table-column prop="required" label="必填" width="70">
              <template #default="{ row }">
                <el-tag :type="row.required === '是' ? 'danger' : 'info'" size="small" effect="plain">
                  {{ row.required }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="desc" label="说明" />
          </el-table>
        </div>
      </el-collapse-transition>

      <!-- 上传区 -->
      <el-upload
        ref="uploadRef"
        class="file-import__upload"
        drag
        :accept="accept"
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
        :on-remove="handleRemove"
        v-model:file-list="fileList"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">把文件拖到这里，或 <em>点击选择文件</em></div>
        <template #tip>
          <div class="el-upload__tip">{{ tip }}</div>
        </template>
      </el-upload>

      <!-- 导入结果 -->
      <div v-if="result" class="file-import__result">
        <el-alert
          :type="result.tone || (failedCount ? 'warning' : 'success')"
          :closable="false"
          show-icon
          :title="result.title"
        >
          <div v-if="result.summary?.length" class="file-import__summary">
            <span v-for="(p, i) in result.summary" :key="i" :class="p.tone">{{ p.text }}</span>
          </div>
        </el-alert>

        <div v-if="result.errors?.length" class="file-import__errors">
          <div class="file-import__errors-title">
            未通过校验的行（修正后可重新导入）
            <span v-if="result.errorsTruncated" class="more">仅显示前 50 行</span>
          </div>
          <el-table :data="result.errors" size="small" border max-height="220">
            <el-table-column prop="row" label="行号" width="70" />
            <el-table-column label="原因" min-width="280">
              <template #default="{ row }">
                <span class="reason">{{ row.reasons.join('；') }}</span>
              </template>
            </el-table-column>
            <el-table-column label="原始内容" min-width="200">
              <template #default="{ row }">
                <span class="raw">{{ rawText(row.raw) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="close(false)">{{ result ? '关闭' : '取消' }}</el-button>
      <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="handleImport">
        {{ uploading ? '导入中…' : '开始导入' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 通用文件导入对话框
 * 学情分析（成绩/答题记录）、课程梳理（大纲/课表）共用：
 * 下载模板 → 上传 csv/xlsx → 逐行校验 → 展示成功/失败明细
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadInstance, UploadRawFile, UploadUserFile } from 'element-plus'
import type { ImportDialogResult, ImportFieldRow, ImportSubmit } from './importTypes'

interface Props {
  modelValue: boolean
  title: string
  /** 三步以内的使用说明 */
  steps: string[]
  /** 字段说明表，可空 */
  fieldRows?: ImportFieldRow[]
  /** 上传控件的 accept，如 '.csv,.xlsx' */
  accept: string
  /** 上传区下方的提示 */
  tip: string
  /** 模板文件名，用于下载时命名 */
  templateName: string
  /** 下载模板 */
  downloadTemplate: () => Promise<void>
  /** 上传并返回展示结果 */
  submit: ImportSubmit
  /** 工具栏右侧的格式提示 */
  acceptText?: string
  /** 结果区是否给「成功」语气（默认按失败行数判断） */
  successTone?: 'success' | 'warning'
}

const props = withDefaults(defineProps<Props>(), {
  fieldRows: () => [],
  acceptText: '',
  successTone: 'success',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'imported', result: ImportDialogResult): void
}>()

const uploadRef = ref<UploadInstance>()
const fileList = ref<UploadUserFile[]>([])
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const showFormat = ref(false)
const result = ref<ImportDialogResult | null>(null)

const failedCount = computed(() => result.value?.errors?.length ?? 0)

function close(value = false): void {
  emit('update:modelValue', value)
}

function reset(): void {
  fileList.value = []
  selectedFile.value = null
  result.value = null
  uploading.value = false
  showFormat.value = false
  uploadRef.value?.clearFiles()
}

function handleFileChange(file: UploadFile): void {
  selectedFile.value = (file.raw as File) ?? null
  result.value = null
}

function handleRemove(): void {
  selectedFile.value = null
  result.value = null
}

function handleExceed(files: File[]): void {
  uploadRef.value?.clearFiles()
  const file = files[0] as unknown as UploadRawFile
  uploadRef.value?.handleStart(file)
  selectedFile.value = file
  result.value = null
}

async function handleDownload(): Promise<void> {
  try {
    await props.downloadTemplate()
    ElMessage.success(`模板已下载（${props.templateName}）`)
  } catch (e) {
    console.warn('模板下载失败', e)
    ElMessage.error('模板下载失败，请稍后重试')
  }
}

async function handleImport(): Promise<void> {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  result.value = null
  try {
    const res = await props.submit(selectedFile.value)
    result.value = res
    if (res.tone === 'error') {
      ElMessage.error(res.title)
    } else if (res.tone === 'warning' || res.errors?.length) {
      ElMessage.warning(res.title)
    } else {
      ElMessage.success(res.title)
    }
    emit('imported', res)
  } catch (e: any) {
    ElMessage.error(e?.message || '导入失败，请检查文件格式')
  } finally {
    uploading.value = false
  }
}

/** 把原始行对象转成简短的展示文本 */
function rawText(raw?: Record<string, unknown>): string {
  if (!raw) return ''
  const vals = Object.entries(raw)
    .filter(([k, v]) => k !== 'row' && v !== undefined && v !== null && String(v).trim() !== '')
    .map(([, v]) => (typeof v === 'object' ? JSON.stringify(v) : String(v)))
  return vals.slice(0, 6).join(' | ').slice(0, 120)
}

/** 供父组件控制对话框 */
defineExpose({ close, reset })
</script>

<style lang="scss" scoped>
.file-import {
  &__steps {
    margin: 0 0 14px 0;
    padding-left: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 8px;

    li {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 13px;
      color: var(--color-text-secondary, #606266);
      line-height: 1.6;
    }

    .num {
      flex-shrink: 0;
      width: 18px;
      height: 18px;
      margin-top: 1px;
      border-radius: 50%;
      background: var(--el-color-primary, #409eff);
      color: #fff;
      font-size: 11px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
  }

  &__toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 12px;
  }

  &__accept {
    margin-left: auto;
    font-size: 12px;
    color: var(--color-text-secondary, #909399);
  }

  &__format {
    margin-bottom: 12px;
  }

  &__upload {
    :deep(.el-upload-dragger) {
      padding: 20px 10px;
    }
  }

  &__result {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  &__summary {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    font-size: 13px;
    margin-top: 4px;

    .ok {
      color: var(--el-color-success, #67c23a);
    }
    .warn {
      color: var(--el-color-warning, #e6a23c);
    }
    .bad {
      color: var(--el-color-danger, #f56c6c);
    }
    .muted {
      color: var(--color-text-secondary, #909399);
    }
  }

  &__errors {
    &-title {
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 6px;
      color: var(--color-text-primary, #303133);

      .more {
        margin-left: 8px;
        font-weight: 400;
        font-size: 12px;
        color: var(--color-text-secondary, #909399);
      }
    }

    .reason {
      color: var(--el-color-danger, #f56c6c);
      font-size: 12px;
    }

    .raw {
      color: var(--color-text-secondary, #909399);
      font-size: 12px;
    }
  }
}
</style>
