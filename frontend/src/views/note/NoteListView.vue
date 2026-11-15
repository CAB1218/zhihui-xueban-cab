<template>
  <div class="note-list">
    <div class="note-list__header">
      <h2>我的笔记</h2>
      <div class="note-list__actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索笔记..."
          prefix-icon="Search"
          clearable
          style="width: 220px"
          @input="handleSearch"
        />
        <el-select v-model="typeFilter" placeholder="类型" clearable style="width: 120px" @change="loadData">
          <el-option label="个人笔记" value="personal" />
          <el-option label="课程笔记" value="course" />
          <el-option label="AI生成" value="ai_generated" />
        </el-select>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon> 新建笔记
        </el-button>
      </div>
    </div>

    <!-- 笔记卡片列表 -->
    <div v-loading="noteStore.isLoading" class="note-list__content">
      <el-row :gutter="16">
        <el-col
          v-for="note in noteStore.notes"
          :key="note.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <el-card
            shadow="hover"
            class="note-list__card"
            @click="goEdit(note.id)"
          >
            <div class="note-list__card-header">
              <h4 class="note-list__card-title">{{ note.title }}</h4>
              <el-tag v-if="note.is_ai_enhanced" type="success" size="small" effect="dark">
                AI增强
              </el-tag>
            </div>
            <p class="note-list__card-summary">
              {{ note.summary || note.content?.substring(0, 100) + '...' || '暂无内容' }}
            </p>
            <div class="note-list__card-tags">
              <el-tag
                v-for="tag in note.tags.slice(0, 3)"
                :key="tag"
                size="small"
                type="info"
                effect="plain"
                class="note-list__tag"
              >
                {{ tag }}
              </el-tag>
            </div>
            <div class="note-list__card-footer">
              <span class="note-list__card-time">{{ formatDate(note.updated_at) }}</span>
              <div class="note-list__card-actions">
                <el-button
                  v-if="note.is_shared"
                  type="primary"
                  link
                  size="small"
                  @click.stop="handleShare(note)"
                >
                  <el-icon><Share /></el-icon> 已分享
                </el-button>
                <el-button
                  type="danger"
                  link
                  size="small"
                  @click.stop="handleDelete(note.id)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="noteStore.notes.length === 0 && !noteStore.isLoading" description="暂无笔记，快创建一个吧" />
    </div>

    <!-- 分页 -->
    <div class="note-list__pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="20"
        :total="noteStore.totalNotes"
        layout="prev, pager, next"
        @current-change="loadData"
      />
    </div>

    <!-- 新建笔记弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建笔记" width="480px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="createForm.title" placeholder="输入笔记标题" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="createForm.note_type" placeholder="选择笔记类型">
            <el-option label="个人笔记" value="personal" />
            <el-option label="课程笔记" value="course" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="createForm.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="添加标签"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 分享弹窗 -->
    <el-dialog v-model="shareDialogVisible" title="分享笔记" width="420px">
      <div v-if="noteStore.shareInfo" class="note-list__share-info">
        <el-input
          :model-value="noteStore.shareInfo.share_url"
          readonly
        >
          <template #append>
            <el-button @click="copyShareLink">复制</el-button>
          </template>
        </el-input>
        <p class="note-list__share-tip">分享链接已生成，可发送给同学查看</p>
      </div>
      <div v-else>
        <p>确认分享该笔记？生成分享链接后其他同学可查看</p>
      </div>
      <template #footer>
        <el-button @click="shareDialogVisible = false">关闭</el-button>
        <el-button v-if="!noteStore.shareInfo" type="primary" @click="confirmShare">生成分享链接</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 笔记列表页
 * 笔记卡片列表 + 搜索筛选 + 新建 + 分享
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Share } from '@element-plus/icons-vue'
import { useNoteStore } from '@/stores/note'
import type { NoteItem } from '@/services/note'

const router = useRouter()
const noteStore = useNoteStore()

const searchQuery = ref<string>('')
const typeFilter = ref<string>('')
const currentPage = ref<number>(1)
const createDialogVisible = ref<boolean>(false)
const shareDialogVisible = ref<boolean>(false)
const sharingNoteId = ref<number | null>(null)

const createForm = reactive({
  title: '',
  note_type: 'personal' as string,
  tags: [] as string[],
})

function loadData(): void {
  noteStore.fetchNotes(currentPage.value, 20, {
    note_type: typeFilter.value || undefined,
    search: searchQuery.value || undefined,
  })
}

function handleSearch(): void {
  currentPage.value = 1
  loadData()
}

function goEdit(noteId: number): void {
  router.push({ name: 'SceneNote', params: { id: noteId } })
}

function handleCreate(): void {
  createDialogVisible.value = true
}

async function submitCreate(): Promise<void> {
  if (!createForm.title.trim()) {
    ElMessage.warning('请输入笔记标题')
    return
  }
  const note = await noteStore.createNote({
    title: createForm.title,
    note_type: createForm.note_type,
    tags: createForm.tags,
  })
  createDialogVisible.value = false
  createForm.title = ''
  createForm.note_type = 'personal'
  createForm.tags = []
  if (note) {
    router.push({ name: 'SceneNote', params: { id: note.id } })
  }
}

async function handleDelete(noteId: number): Promise<void> {
  try {
    await ElMessageBox.confirm('确定删除该笔记？删除后不可恢复', '确认删除', { type: 'warning' })
    await noteStore.deleteNote(noteId)
  } catch {
    // 用户取消
  }
}

function handleShare(note: NoteItem): void {
  sharingNoteId.value = note.id
  shareDialogVisible.value = true
}

async function confirmShare(): Promise<void> {
  if (sharingNoteId.value !== null) {
    await noteStore.shareNote(sharingNoteId.value)
  }
}

function copyShareLink(): void {
  if (noteStore.shareInfo?.share_url) {
    navigator.clipboard.writeText(noteStore.shareInfo.share_url)
    ElMessage.success('链接已复制到剪贴板')
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.note-list {
  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      font-size: 22px;
      font-weight: 700;
      color: var(--color-text-primary);
      margin: 0;
    }
  }

  &__actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  &__content {
    min-height: 300px;
  }

  &__card {
    margin-bottom: 16px;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    :deep(.el-card__body) {
      padding: 16px;
    }
  }

  &__card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
  }

  &__card-title {
    font-size: 15px;
    font-weight: 600;
    margin: 0;
    color: #303133;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__card-summary {
    font-size: 13px;
    color: #909399;
    line-height: 1.6;
    margin: 0 0 10px;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__card-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 10px;
  }

  &__tag {
    font-size: 11px;
  }

  &__card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 8px;
    border-top: 1px solid #f0f0f0;
  }

  &__card-time {
    font-size: 12px;
    color: #c0c4cc;
  }

  &__card-actions {
    display: flex;
    gap: 4px;
  }

  &__pagination {
    display: flex;
    justify-content: center;
    margin-top: 24px;
  }

  &__share-info {
    :deep(.el-input-group__append) {
      cursor: pointer;
    }
  }

  &__share-tip {
    margin-top: 12px;
    font-size: 13px;
    color: #909399;
  }
}
</style>
