<template>
  <div class="my-resources">
    <div class="my-resources__header">
      <h2>我的资源</h2>
      <div class="my-resources__actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索资源..."
          prefix-icon="Search"
          clearable
          style="width: 200px"
          @input="handleSearch"
        />
        <el-select v-model="typeFilter" placeholder="类型筛选" clearable style="width: 120px" @change="loadData">
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="docx" />
          <el-option label="PPT" value="pptx" />
          <el-option label="视频" value="video" />
          <el-option label="图片" value="image" />
        </el-select>
        <el-button-group>
          <el-button :type="viewMode === 'grid' ? 'primary' : 'default'" @click="viewMode = 'grid'">
            <el-icon><Grid /></el-icon>
          </el-button>
          <el-button :type="viewMode === 'list' ? 'primary' : 'default'" @click="viewMode = 'list'">
            <el-icon><List /></el-icon>
          </el-button>
        </el-button-group>
        <el-button type="primary" @click="goUpload">
          <el-icon><Plus /></el-icon> 上传资源
        </el-button>
      </div>
    </div>

    <!-- 拖拽上传区 -->
    <UploadZone @files-selected="handleFilesSelected" />

    <!-- 批量操作 -->
    <div v-if="selectedIds.length > 0" class="my-resources__batch">
      <span>已选择 {{ selectedIds.length }} 项</span>
      <el-button type="danger" size="small" @click="batchDelete">批量删除</el-button>
    </div>

    <!-- 资源列表 -->
    <div v-loading="resourceStore.loading" class="my-resources__content">
      <!-- 网格模式 -->
      <el-row v-if="viewMode === 'grid'" :gutter="16">
        <el-col v-for="r in resourceStore.resources" :key="r.id" :xs="12" :sm="8" :md="6" :lg="4">
          <ResourceCard :resource="r" @click="goDetail(r.id)">
            <template #header>
              <el-checkbox v-model="selectedMap[r.id]" @change="toggleSelect(r.id)" />
            </template>
          </ResourceCard>
        </el-col>
      </el-row>

      <!-- 列表模式 -->
      <div v-else class="my-resources__list">
        <div v-for="r in resourceStore.resources" :key="r.id" class="my-resources__list-item">
          <el-checkbox v-model="selectedMap[r.id]" @change="toggleSelect(r.id)" />
          <ResourceCard :resource="r" @click="goDetail(r.id)" />
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="my-resources__pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="20"
        :total="resourceStore.total"
        layout="prev, pager, next"
        @current-change="loadData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 我的资源视图
 * 网格/列表切换 + 资源卡片 + 拖拽上传 + 批量操作
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Grid, List, Plus } from '@element-plus/icons-vue'
import { useResourceStore } from '@/stores/resource'
import ResourceCard from '@/components/resource/ResourceCard.vue'
import UploadZone from '@/components/resource/UploadZone.vue'

const router = useRouter()
const resourceStore = useResourceStore()

const searchQuery = ref('')
const typeFilter = ref('')
const viewMode = ref<'grid' | 'list'>('grid')
const currentPage = ref(1)
const selectedMap = reactive<Record<number, boolean>>({})

const selectedIds = ref<number[]>([])

function toggleSelect(id: number): void {
  if (selectedMap[id]) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
  } else {
    selectedIds.value = selectedIds.value.filter((i) => i !== id)
  }
}

function loadData(): void {
  resourceStore.loadResources({
    page: currentPage.value,
    page_size: 20,
    resource_type: typeFilter.value || undefined,
    search: searchQuery.value || undefined,
  })
}

function handleSearch(): void {
  currentPage.value = 1
  loadData()
}

function goUpload(): void {
  router.push({ name: 'ResourceUpload' })
}

function goDetail(id: number): void {
  router.push({ name: 'ResourceDetail', params: { id } })
}

async function handleFilesSelected(files: File[]): Promise<void> {
  for (const file of files) {
    try {
      await resourceStore.uploadFile(file, { title: file.name })
      ElMessage.success(`${file.name} 上传成功`)
    } catch {
      ElMessage.error(`${file.name} 上传失败`)
    }
  }
  loadData()
}

async function batchDelete(): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 个资源?`, '确认', { type: 'warning' })
    for (const id of selectedIds.value) {
      await resourceStore.deleteResource(id)
    }
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    Object.keys(selectedMap).forEach((k) => delete selectedMap[Number(k)])
    loadData()
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.my-resources {
  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-lg);

    h2 {
      font-size: 22px;
      font-weight: 700;
      color: var(--color-text-primary);
    }
  }

  &__actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  &__batch {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    background: var(--color-bg-tertiary);
    border-radius: var(--border-radius-sm);
    margin-bottom: 12px;
    font-size: 14px;
  }

  &__content {
    min-height: 300px;
    margin-top: 16px;
  }

  &__list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__list-item {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  &__pagination {
    display: flex;
    justify-content: center;
    margin-top: var(--spacing-lg);
  }
}
</style>
