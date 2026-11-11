<template>
  <el-dialog
    v-model="visible"
    title="导出对话"
    width="520px"
    :close-on-click-modal="false"
    @open="handleOpen"
  >
    <!-- 格式选择 -->
    <div class="export-dialog__format">
      <p class="export-dialog__label">选择导出格式：</p>
      <el-radio-group v-model="selectedFormat" :disabled="agentStore.exportLoading">
        <el-radio-button value="markdown">
          <el-icon><Document /></el-icon>
          Markdown (.md)
        </el-radio-button>
        <el-radio-button value="pdf">
          <el-icon><Files /></el-icon>
          PDF (.pdf)
        </el-radio-button>
      </el-radio-group>
      <p class="export-dialog__hint">
        {{
          selectedFormat === 'pdf'
            ? 'PDF 格式适合打印和分享，包含完整对话内容和引用来源。'
            : 'Markdown 格式适合二次编辑，保留原始文本结构。'
        }}
      </p>
    </div>

    <!-- 导出记录列表 -->
    <div v-if="agentStore.exportRecords.length > 0" class="export-dialog__history">
      <el-divider content-position="left">导出历史</el-divider>
      <el-table :data="agentStore.exportRecords" size="small" max-height="200">
        <el-table-column prop="export_format" label="格式" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.export_format === 'pdf' ? 'danger' : 'info'">
              {{ row.export_format.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="statusTagType(row.status)"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="80">
          <template #default="{ row }">
            {{ row.file_size ? formatFileSize(row.file_size) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="140">
          <template #default="{ row }">
            {{ row.created_at ? formatTime(row.created_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'completed'"
              type="primary"
              link
              size="small"
              @click="handleDownload(row.id)"
            >
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button
        type="primary"
        :loading="agentStore.exportLoading"
        :disabled="agentStore.exportLoading"
        @click="handleExport"
      >
        <el-icon><Download /></el-icon>
        创建导出
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * AI4Edu 对话导出对话框
 * 支持 Markdown / PDF 格式导出，展示导出历史和下载链接
 */
import { ref, computed } from 'vue'
import { Document, Files, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAgentStore } from '@/stores/agent'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const agentStore = useAgentStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val),
})

const selectedFormat = ref<string>('markdown')

/** 对话框打开时加载导出历史 */
async function handleOpen(): Promise<void> {
  await agentStore.fetchExportRecords()
}

/** 创建导出 */
async function handleExport(): Promise<void> {
  const record = await agentStore.createExport(selectedFormat.value)
  if (record) {
    // 开始轮询状态
    ElMessage.info('正在生成导出文件...')
    const finalRecord = await agentStore.pollExportStatus(record.id)
    if (finalRecord?.status === 'completed') {
      ElMessage.success('导出完成！可点击下载按钮获取文件')
    } else if (finalRecord?.status === 'failed') {
      ElMessage.error(`导出失败: ${finalRecord.error_msg || '未知错误'}`)
    } else {
      ElMessage.warning('导出仍在处理中，请稍后刷新查看')
    }
  }
}

/** 下载导出文件 */
async function handleDownload(exportId: number): Promise<void> {
  await agentStore.downloadExport(exportId)
}

/** 状态标签类型 */
function statusTagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    completed: 'success',
    processing: 'warning',
    pending: 'info',
    failed: 'danger',
  }
  return map[status] || 'info'
}

/** 状态标签文本 */
function statusLabel(status: string): string {
  const map: Record<string, string> = {
    completed: '已完成',
    processing: '处理中',
    pending: '等待中',
    failed: '失败',
  }
  return map[status] || status
}

/** 格式化文件大小 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** 格式化时间 */
function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style lang="scss" scoped>
.export-dialog {
  &__format {
    margin-bottom: 16px;
  }

  &__label {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 8px;
    color: #333;
  }

  &__hint {
    font-size: 12px;
    color: #999;
    margin-top: 8px;
    line-height: 1.5;
  }

  &__history {
    margin-top: 8px;
  }
}
</style>
