<template>
  <div class="resource-detail">
    <div class="resource-detail__header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <h2>{{ resource?.title || '资源详情' }}</h2>
    </div>

    <div v-loading="resourceStore.loading" class="resource-detail__content">
      <el-row :gutter="16">
        <!-- 左侧：文件预览 -->
        <el-col :xs="24" :lg="16">
          <el-card>
            <h3>文件预览</h3>
            <FilePreview
              v-if="resource?.preview_url"
              :preview-url="resource.preview_url"
              :resource-type="resource.resource_type"
              :mime-type="resource.mime_type"
              @download="handleDownload"
            />
            <el-empty v-else description="暂无预览" />
          </el-card>
        </el-col>

        <!-- 右侧：详情信息 -->
        <el-col :xs="24" :lg="8">
          <!-- AI摘要 -->
          <el-card class="resource-detail__card">
            <template #header>
              <div class="resource-detail__card-header">
                <span>AI 摘要</span>
                <el-button size="small" type="primary" plain :loading="summaryLoading" @click="generateSummary">
                  生成摘要
                </el-button>
              </div>
            </template>
            <p v-if="summary" class="resource-detail__summary">{{ summary }}</p>
            <p v-else class="resource-detail__summary-placeholder">点击"生成摘要"获取 AI 摘要</p>
          </el-card>

          <!-- 基本信息 -->
          <el-card class="resource-detail__card">
            <template #header><span>基本信息</span></template>
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="类型">
                <el-tag size="small">{{ resource?.resource_type }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="大小">{{ formatSize(resource?.file_size || 0) }}</el-descriptions-item>
              <el-descriptions-item label="上传时间">{{ resource?.created_at }}</el-descriptions-item>
              <el-descriptions-item label="下载次数">{{ resource?.download_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="浏览次数">{{ resource?.view_count || 0 }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 标签 -->
          <el-card class="resource-detail__card">
            <template #header><span>标签</span></template>
            <TagEditor
              v-model="tags"
              :resource-id="resourceId"
              @auto-tag="handleAutoTag"
            />
          </el-card>

          <!-- 关联知识点 -->
          <el-card class="resource-detail__card">
            <template #header><span>关联知识点</span></template>
            <div v-if="linkedNodes.length > 0" class="resource-detail__nodes">
              <el-tag
                v-for="node in linkedNodes"
                :key="node"
                closable
                size="small"
                @close="unlinkNode(node)"
              >
                {{ node }}
              </el-tag>
            </div>
            <p v-else class="resource-detail__no-nodes">暂无关联知识点</p>
          </el-card>

          <!-- 版本历史 -->
          <el-card class="resource-detail__card">
            <template #header><span>版本历史</span></template>
            <el-timeline>
              <el-timeline-item timestamp="当前版本" placement="top">
                版本 1.0 - 上传
              </el-timeline-item>
            </el-timeline>
          </el-card>

          <!-- 操作 -->
          <div class="resource-detail__actions">
            <el-button type="primary" @click="handleDownload">下载</el-button>
            <el-button @click="toggleFavorite">
              {{ isFavorited ? '取消收藏' : '收藏' }}
            </el-button>
            <el-button type="danger" plain @click="handleDelete">删除</el-button>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 资源详情视图
 * 文件预览 + AI摘要 + 关联知识点 + 版本历史
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useResourceStore } from '@/stores/resource'
import { resourceApi } from '@/services/resource'
import FilePreview from '@/components/resource/FilePreview.vue'
import TagEditor from '@/components/resource/TagEditor.vue'

const route = useRoute()
const router = useRouter()
const resourceStore = useResourceStore()

const resourceId = computed(() => Number(route.params.id))
const resource = computed(() => resourceStore.currentResource)
const summary = ref('')
const summaryLoading = ref(false)
const isFavorited = ref(false)
const tags = ref<string[]>([])
const linkedNodes = ref<string[]>([])

function goBack(): void {
  router.back()
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

async function generateSummary(): Promise<void> {
  summaryLoading.value = true
  try {
    summary.value = await resourceApi.summarize(resourceId.value)
  } catch {
    ElMessage.error('摘要生成失败')
  } finally {
    summaryLoading.value = false
  }
}

async function handleAutoTag(): Promise<void> {
  try {
    const newTags = await resourceApi.autoTag(resourceId.value)
    tags.value = newTags
    ElMessage.success('标签生成成功')
  } catch {
    ElMessage.error('标签生成失败')
  }
}

async function handleDelete(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定删除该资源?', '确认', { type: 'warning' })
    await resourceStore.deleteResource(resourceId.value)
    ElMessage.success('删除成功')
    router.push({ name: 'MyResources' })
  } catch {
    // 用户取消
  }
}

async function toggleFavorite(): Promise<void> {
  try {
    isFavorited.value = await resourceApi.toggleFavorite(resourceId.value)
  } catch {
    ElMessage.error('操作失败')
  }
}

function handleDownload(): void {
  if (resource.value?.preview_url) {
    window.open(resource.value.preview_url, '_blank')
  }
}

async function unlinkNode(nodeId: string): Promise<void> {
  try {
    await resourceApi.unlinkFromNode(resourceId.value, nodeId)
    linkedNodes.value = linkedNodes.value.filter((n) => n !== nodeId)
  } catch {
    ElMessage.error('取消关联失败')
  }
}

async function loadDetail(): Promise<void> {
  await resourceStore.loadResourceDetail(resourceId.value)
  if (resource.value) {
    tags.value = resource.value.tags || []
    const metadata = resource.value.metadata || {}
    linkedNodes.value = (metadata.linked_nodes as string[]) || []
  }
}

onMounted(() => {
  loadDetail()
})

watch(resource, (val) => {
  if (val) {
    tags.value = val.tags || []
    const metadata = val.metadata || {}
    linkedNodes.value = (metadata.linked_nodes as string[]) || []
  }
})
</script>

<style lang="scss" scoped>
.resource-detail {
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

  &__card {
    margin-bottom: var(--spacing-md);
  }

  &__card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  &__summary {
    font-size: 14px;
    line-height: 1.6;
    color: var(--color-text-regular);
  }

  &__summary-placeholder {
    font-size: 13px;
    color: var(--color-text-placeholder);
  }

  &__nodes {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  &__no-nodes {
    font-size: 13px;
    color: var(--color-text-placeholder);
  }

  &__actions {
    display: flex;
    gap: 8px;
    margin-top: var(--spacing-md);
  }
}
</style>
