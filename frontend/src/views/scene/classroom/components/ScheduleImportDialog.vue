<template>
  <el-dialog
    :model-value="modelValue"
    title="导入课表"
    width="720px"
    :close-on-click-modal="false"
    class="schedule-import"
    @update:model-value="close"
    @closed="reset"
  >
    <div class="schedule-import__body">
      <!-- 三步引导 -->
      <ol class="schedule-import__steps">
        <li><span class="num">1</span>下载模板，按表头填写课程（也可直接用学校导出的课表，列名支持中英文常见写法）</li>
        <li><span class="num">2</span>上传 <code>.csv</code> 或 <code>.xlsx</code> 文件，系统逐行校验</li>
        <li><span class="num">3</span>导入成功后，「今日课表」和「今日课程」会自动更新</li>
      </ol>

      <div class="schedule-import__toolbar">
        <el-button :icon="Download" plain @click="handleDownload">下载导入模板</el-button>
        <el-button link type="primary" @click="showFormat = !showFormat">
          {{ showFormat ? '收起字段说明' : '查看字段说明' }}
        </el-button>
        <div class="schedule-import__mode">
          <span class="label">导入方式</span>
          <el-radio-group v-model="mode" size="small">
            <el-radio-button value="replace">覆盖原课表</el-radio-button>
            <el-radio-button value="append">追加到现有课表</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <el-collapse-transition>
        <div v-show="showFormat" class="schedule-import__format">
          <el-table :data="FIELD_ROWS" size="small" border>
            <el-table-column prop="field" label="列名" width="110" />
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
        class="schedule-import__upload"
        drag
        accept=".csv,.xlsx"
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
        :on-remove="handleRemove"
        v-model:file-list="fileList"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          把课表文件拖到这里，或 <em>点击选择文件</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .csv / .xlsx，单个文件不超过 5MB，最多 500 条课程记录
          </div>
        </template>
      </el-upload>

      <!-- 导入结果 -->
      <div v-if="result" class="schedule-import__result">
        <el-alert
          :type="result.failed > 0 ? 'warning' : 'success'"
          :closable="false"
          show-icon
          :title="resultTitle"
        >
          <div class="schedule-import__summary">
            <span>文件共 {{ result.total_rows }} 行</span>
            <span v-if="result.dry_run" class="ok">可导入 {{ result.valid ?? 0 }} 条</span>
            <span v-else class="ok">成功 {{ result.imported }} 条</span>
            <span v-if="result.skipped" class="skip">重复跳过 {{ result.skipped }} 条</span>
            <span v-if="result.failed" class="bad">失败 {{ result.failed }} 行</span>
            <span v-if="result.dry_run" class="pending">（尚未写入课表）</span>
          </div>
        </el-alert>

        <div v-if="result.errors.length" class="schedule-import__errors">
          <div class="schedule-import__errors-title">
            未通过校验的行（修正后可重新导入）
            <span v-if="result.errors_truncated" class="more">仅显示前 50 行</span>
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
      <el-button @click="close(false)">{{ result && !pendingConfirm ? '关闭' : '取消' }}</el-button>
      <el-button
        type="primary"
        :loading="uploading"
        :disabled="!fileList.length"
        @click="handleImport"
      >
        {{ primaryLabel }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 课表导入对话框
 * - 下载模板 / 上传 csv·xlsx / 覆盖或追加 / 逐行校验结果
 * - 导入成功后通知父组件刷新今日课表
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadInstance, UploadRawFile, UploadUserFile } from 'element-plus'
import scheduleApi, { type ScheduleImportResult } from '@/services/schedule'

interface Props {
  modelValue: boolean
}

defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'imported', result: ScheduleImportResult): void
}>()

const FIELD_ROWS = [
  { field: '课程名称', required: '是', desc: '必填，如「高等数学」；也识别 课程 / 科目 / course' },
  { field: '星期', required: '是', desc: '周一~周日、星期一~星期日、1~7、Mon~Sun 都支持' },
  { field: '开始时间', required: '是', desc: '08:00 / 8:00 / 0800 / 8点 均可' },
  { field: '结束时间', required: '是', desc: '09:40 / 9点40 均可；也可只写一列「上课时间」= 08:00-09:40' },
  { field: '上课地点', required: '否', desc: '如「教一101」，也识别 教室 / location' },
  { field: '任课教师', required: '否', desc: '如「张伟」，也识别 教师 / 老师 / teacher' },
  { field: '周次', required: '否', desc: '如「1-16」「1,3,5」，留空表示全学期' },
]

const uploadRef = ref<UploadInstance>()
const fileList = ref<UploadUserFile[]>([])
const selectedFile = ref<File | null>(null)
const mode = ref<'replace' | 'append'>('replace')
const uploading = ref(false)
const result = ref<ScheduleImportResult | null>(null)
const showFormat = ref(false)
/** 校验发现有坏行时进入「待确认」状态，避免一次点击就把原课表覆盖掉 */
const pendingConfirm = ref(false)

const primaryLabel = computed(() => {
  if (uploading.value) return '导入中…'
  if (pendingConfirm.value) {
    const valid = result.value?.valid ?? 0
    return mode.value === 'replace' ? `仍要覆盖导入 ${valid} 条` : `仍要追加 ${valid} 条`
  }
  return '开始导入'
})

const resultTitle = computed(() => {
  if (!result.value) return ''
  if (result.value.dry_run) {
    return result.value.failed > 0
      ? '文件里有需要修正的行，确认后只会导入有效行'
      : '校验通过，正在写入课表…'
  }
  if (result.value.imported === 0 && result.value.skipped > 0) {
    return '这些课程已经在课表里了，无需重复导入'
  }
  if (result.value.imported === 0) return '没有导入任何课程，请按下方原因修正文件后重试'
  if (result.value.failed > 0) return '部分导入成功，失败行未写入'
  return '课表导入成功'
})

function close(value = false): void {
  emit('update:modelValue', value)
}

function reset(): void {
  fileList.value = []
  selectedFile.value = null
  result.value = null
  uploading.value = false
  showFormat.value = false
  pendingConfirm.value = false
  uploadRef.value?.clearFiles()
}

function handleFileChange(file: UploadFile): void {
  selectedFile.value = (file.raw as File) ?? null
  result.value = null
  pendingConfirm.value = false
}

function handleRemove(): void {
  selectedFile.value = null
  result.value = null
  pendingConfirm.value = false
}

function handleExceed(files: File[]): void {
  uploadRef.value?.clearFiles()
  const file = files[0] as unknown as UploadRawFile
  uploadRef.value?.handleStart(file)
  selectedFile.value = file
  result.value = null
  pendingConfirm.value = false
}

async function handleDownload(): Promise<void> {
  try {
    await scheduleApi.downloadTemplate()
  } catch (e) {
    console.warn('模板下载失败', e)
    ElMessage.error('模板下载失败，请稍后重试')
  }
}

async function handleImport(): Promise<void> {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择课表文件')
    return
  }
  // 已经确认过（预览显示有坏行），这次真正写库
  if (pendingConfirm.value) {
    await doImport()
    return
  }

  uploading.value = true
  result.value = null
  try {
    // 先校验：有坏行时先给用户看清楚，避免一次点击覆盖掉原课表
    const { result: preview, message } = await scheduleApi.importFile(selectedFile.value, mode.value, true)
    if (preview.failed > 0) {
      result.value = preview
      pendingConfirm.value = true
      ElMessage.warning(message || '有行未通过校验，请确认后再次点击导入')
      return
    }
    uploading.value = false
    await doImport()
  } catch (e: any) {
    ElMessage.error(e?.message || '校验失败，请检查文件格式')
  } finally {
    uploading.value = false
  }
}

/** 真正写库 */
async function doImport(): Promise<void> {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    const { result: res, message } = await scheduleApi.importFile(selectedFile.value, mode.value, false)
    result.value = res
    pendingConfirm.value = false
    if (res.imported > 0) {
      ElMessage.success(message || `成功导入 ${res.imported} 条课表`)
      emit('imported', res)
    } else if (res.skipped > 0) {
      ElMessage.info(message || '这些课程已经在课表里了')
    } else {
      ElMessage.warning(message || '没有可导入的有效行，请按提示修正后重试')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '导入失败，请检查文件格式')
  } finally {
    uploading.value = false
  }
}

/** 把原始行对象转成简短的展示文本 */
function rawText(raw?: Record<string, string>): string {
  if (!raw) return ''
  const vals = Object.values(raw).filter((v) => v !== undefined && v !== null && String(v).trim() !== '')
  return vals.slice(0, 6).join(' | ').slice(0, 120)
}
</script>

<style lang="scss" scoped>
.schedule-import {
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

    code {
      padding: 1px 5px;
      border-radius: 4px;
      background: var(--color-fill-light, #f2f3f5);
      font-size: 12px;
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

  &__mode {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;

    .label {
      font-size: 13px;
      color: var(--color-text-secondary, #606266);
    }
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
    .skip {
      color: var(--el-color-warning, #e6a23c);
    }
    .bad {
      color: var(--el-color-danger, #f56c6c);
    }
    .pending {
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
      word-break: break-all;
    }
  }
}
</style>
