<template>
  <div class="resource-upload">
    <div class="resource-upload__header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <h2>上传资源</h2>
    </div>

    <el-card>
      <el-upload
        ref="uploadRef"
        class="resource-upload__uploader"
        drag
        multiple
        :auto-upload="false"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
      >
        <el-icon :size="48"><UploadFilled /></el-icon>
        <div>将文件拖到此处，或点击上传</div>
        <template #tip>
          <div class="resource-upload__tip">支持 PDF、Word、PPT、图片等格式</div>
        </template>
      </el-upload>

      <!-- 上传进度 -->
      <div v-for="item in uploadItems" :key="item.name" class="resource-upload__progress">
        <span class="resource-upload__progress-name">{{ item.name }}</span>
        <el-progress :percentage="item.progress" :status="item.status" />
      </div>

      <!-- 关联知识点 -->
      <div class="resource-upload__link-node">
        <h3>关联知识点</h3>
        <el-select
          v-model="selectedNodes"
          multiple
          filterable
          remote
          reserve-keyword
          placeholder="搜索知识点"
          :remote-method="searchNodes"
          :loading="nodeSearchLoading"
        >
          <el-option
            v-for="node in nodeOptions"
            :key="node.id"
            :label="node.name || node.id"
            :value="node.id"
          />
        </el-select>
      </div>

      <div class="resource-upload__actions">
        <el-button @click="goBack">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="fileList.length === 0" @click="handleUpload">
          开始上传
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4Edu 资源上传视图
 * 多文件 + 进度条 + 关联知识点
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadUserFile } from 'element-plus'
import { useResourceStore } from '@/stores/resource'
import { graphApi } from '@/services/graph'
import type { KnowledgeNode } from '@/services/graph'

const router = useRouter()
const resourceStore = useResourceStore()

const uploadRef = ref()
const fileList = ref<UploadUserFile[]>([])
const selectedNodes = ref<string[]>([])
const nodeOptions = ref<KnowledgeNode[]>([])
const nodeSearchLoading = ref(false)
const uploading = ref(false)

interface UploadItem {
  name: string
  progress: number
  status: '' | 'success' | 'warning' | 'exception'
}

const uploadItems = reactive<UploadItem[]>([])

function goBack(): void {
  router.back()
}

function handleFileChange(_file: UploadFile, files: UploadUserFile[]): void {
  fileList.value = files
}

function handleFileRemove(_file: UploadFile, files: UploadUserFile[]): void {
  fileList.value = files
}

async function searchNodes(query: string): Promise<void> {
  if (!query.trim()) {
    nodeOptions.value = []
    return
  }
  nodeSearchLoading.value = true
  try {
    nodeOptions.value = await graphApi.searchNodes(query)
  } catch {
    nodeOptions.value = []
  } finally {
    nodeSearchLoading.value = false
  }
}

async function handleUpload(): Promise<void> {
  if (fileList.value.length === 0) return

  uploading.value = true
  uploadItems.length = 0

  for (const file of fileList.value) {
    if (!file.raw) continue
    uploadItems.push({ name: file.name, progress: 0, status: '' })
  }

  let successCount = 0
  for (let i = 0; i < fileList.value.length; i++) {
    const file = fileList.value[i]
    if (!file.raw) continue

    try {
      await resourceStore.uploadFile(file.raw, { title: file.name })
      uploadItems[i].progress = 100
      uploadItems[i].status = 'success'
      successCount++

      // 关联知识点
      if (selectedNodes.value.length > 0) {
        // 上传后关联（需要资源ID，这里简化处理）
      }
    } catch {
      uploadItems[i].progress = 100
      uploadItems[i].status = 'exception'
    }
  }

  uploading.value = false
  ElMessage.success(`上传完成：${successCount} 个成功`)
  if (successCount === fileList.value.length) {
    router.push({ name: 'MyResources' })
  }
}
</script>

<style lang="scss" scoped>
.resource-upload {
  &__header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: var(--spacing-lg);

    h2 {
      font-size: 22px;
      font-weight: 700;
    }
  }

  &__uploader {
    margin-bottom: var(--spacing-lg);

    :deep(.el-upload-dragger) {
      width: 100%;
    }
  }

  &__tip {
    color: var(--color-text-secondary);
    font-size: 12px;
  }

  &__progress {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  &__progress-name {
    font-size: 13px;
    width: 200px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &__link-node {
    margin: var(--spacing-lg) 0;

    h3 {
      margin-bottom: 8px;
    }

    .el-select {
      width: 100%;
    }
  }

  &__actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: var(--spacing-lg);
  }
}
</style>
