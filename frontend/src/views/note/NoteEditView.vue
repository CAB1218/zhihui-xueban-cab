<template>
  <div class="note-edit">
    <!-- 顶部工具栏 -->
    <div class="note-edit__toolbar">
      <div class="note-edit__toolbar-left">
        <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
        <el-input
          v-model="editorState.title.value"
          placeholder="笔记标题"
          class="note-edit__title-input"
          size="large"
        />
      </div>
      <div class="note-edit__toolbar-right">
        <el-tag :type="saveStatusType" size="small" effect="plain">
          {{ editorState.saveStatusText.value }}
        </el-tag>
        <el-button :loading="noteStore.aiEnhanceLoading" @click="handleAIEnhance">
          <el-icon><MagicStick /></el-icon> AI增强
        </el-button>
        <el-button @click="showVersionDialog = true">
          <el-icon><Clock /></el-icon> 版本
        </el-button>
        <el-button @click="handleShare">
          <el-icon><Share /></el-icon> 分享
        </el-button>
        <el-button type="primary" :disabled="!editorState.canSave.value" @click="editorState.manualSave()">
          保存
        </el-button>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="note-edit__body">
      <!-- 左侧编辑区 -->
      <div class="note-edit__editor">
        <!-- 格式工具栏 -->
        <div class="note-edit__format-bar">
          <el-button-group>
            <el-button size="small" @click="editorState.wrapSelection('**', '**')" title="粗体">
              <strong>B</strong>
            </el-button>
            <el-button size="small" @click="editorState.wrapSelection('*', '*')" title="斜体">
              <em>I</em>
            </el-button>
            <el-button size="small" @click="editorState.wrapSelection('~~', '~~')" title="删除线">
              <del>S</del>
            </el-button>
            <el-button size="small" @click="editorState.insertAtCursor('\n# ')" title="标题">
              H
            </el-button>
            <el-button size="small" @click="editorState.insertAtCursor('\n- ')" title="列表">
              <el-icon><List /></el-icon>
            </el-button>
            <el-button size="small" @click="editorState.insertAtCursor('\n```\n\n```')" title="代码块">
              <el-icon><Document /></el-icon>
            </el-button>
          </el-button-group>
          <div class="note-edit__mode-toggle">
            <el-switch
              v-model="isPreviewMode"
              active-text="预览"
              inactive-text="编辑"
              size="small"
            />
          </div>
        </div>

        <!-- 编辑器内容 -->
        <div class="note-edit__content">
          <textarea
            v-show="!isPreviewMode"
            ref="textareaRef"
            v-model="editorState.content.value"
            class="note-edit__textarea"
            placeholder="开始记录你的笔记..."
            @select="handleTextareaSelect"
            @click="updateCursorPosition"
            @keyup="updateCursorPosition"
          ></textarea>
          <div
            v-show="isPreviewMode"
            class="note-edit__preview"
            v-html="renderMarkdown(editorState.content.value)"
          ></div>
        </div>
      </div>

      <!-- 右侧AI面板 -->
      <div v-if="editorState.aiPanelVisible.value" class="note-edit__ai-panel">
        <div class="note-edit__ai-panel-header">
          <h4>AI 助手</h4>
          <el-button link @click="editorState.aiPanelVisible.value = false">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>

        <div class="note-edit__ai-actions">
          <el-button size="small" @click="editorState.aiEnhance('summarize')">摘要生成</el-button>
          <el-button size="small" @click="editorState.aiEnhance('extract_points')">提取知识点</el-button>
          <el-button size="small" @click="editorState.aiEnhance('expand')">内容扩展</el-button>
          <el-button size="small" @click="editorState.aiEnhance('correct')">纠错润色</el-button>
        </div>

        <div class="note-edit__ai-result">
          <h5 v-if="noteStore.aiEnhanceResult">AI结果</h5>
          <div v-if="noteStore.aiEnhanceResult" class="note-edit__ai-result-content">
            <p v-if="noteStore.aiEnhanceResult.summary">
              <strong>摘要：</strong>{{ noteStore.aiEnhanceResult.summary }}
            </p>
            <div v-if="noteStore.aiEnhanceResult.knowledge_points">
              <strong>知识点：</strong>
              <ul>
                <li v-for="(point, idx) in (noteStore.aiEnhanceResult.knowledge_points as string[])" :key="idx">{{ point }}</li>
              </ul>
            </div>
          </div>
          <el-empty v-else description="选择AI功能增强你的笔记" :image-size="60" />
        </div>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="note-edit__status-bar">
      <span>字数：{{ editorState.wordCount.value }}</span>
      <span>字符：{{ editorState.charCount.value }}</span>
      <span>版本：v{{ editorState.currentVersion.value }}</span>
      <span :class="['note-edit__save-status', `note-edit__save-status--${editorState.saveStatus.value}`]">
        {{ editorState.saveStatusText.value }}
      </span>
    </div>

    <!-- 版本历史弹窗 -->
    <el-dialog v-model="showVersionDialog" title="版本历史" width="560px">
      <el-timeline>
        <el-timeline-item
          v-for="ver in noteStore.versions"
          :key="ver.id"
          :timestamp="formatDate(ver.created_at)"
          placement="top"
        >
          <div class="note-edit__version-item">
            <span>版本 {{ ver.version }}</span>
            <span v-if="ver.change_summary" class="note-edit__version-summary">{{ ver.change_summary }}</span>
            <el-button type="primary" link size="small" @click="editorState.revertToVersion(ver.version)">
              回退到此版本
            </el-button>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="noteStore.versions.length === 0" description="暂无版本记录" :image-size="60" />
    </el-dialog>

    <!-- 分享弹窗 -->
    <el-dialog v-model="showShareDialog" title="分享笔记" width="420px">
      <div v-if="noteStore.shareInfo" class="note-edit__share-info">
        <el-input :model-value="noteStore.shareInfo.share_url" readonly>
          <template #append>
            <el-button @click="copyShareLink">复制</el-button>
          </template>
        </el-input>
      </div>
      <div v-else>
        <p>确认分享该笔记？</p>
      </div>
      <template #footer>
        <el-button @click="showShareDialog = false">关闭</el-button>
        <el-button v-if="!noteStore.shareInfo" type="primary" @click="confirmShare">生成分享链接</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 笔记编辑页
 * 顶部工具栏 + 左侧编辑区 + 右侧AI面板 + 底部状态栏
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, MagicStick, Clock, Share, Close, List, Document } from '@element-plus/icons-vue'
import { useNoteStore } from '@/stores/note'
import { useNoteEditor } from '@/composables/useNoteEditor'

const route = useRoute()
const router = useRouter()
const noteStore = useNoteStore()

const noteId = computed<number | null>(() => {
  const id = route.params.id
  return id ? Number(id) : null
})

const editorState = useNoteEditor(noteId)

const isPreviewMode = ref<boolean>(false)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const showVersionDialog = ref<boolean>(false)
const showShareDialog = ref<boolean>(false)

/** 保存状态对应的Tag类型 */
const saveStatusType = computed(() => {
  const map: Record<string, string> = {
    idle: 'info',
    saving: 'warning',
    saved: 'success',
    error: 'danger',
  }
  return map[editorState.saveStatus.value] || 'info'
})

/** 处理文本选区 */
function handleTextareaSelect(event: Event): void {
  const target = event.target as HTMLTextAreaElement
  editorState.handleSelectionChange(target.selectionStart, target.selectionEnd, target.value)
}

/** 更新光标位置 */
function updateCursorPosition(): void {
  if (textareaRef.value) {
    editorState.handleSelectionChange(
      textareaRef.value.selectionStart,
      textareaRef.value.selectionEnd,
      textareaRef.value.value
    )
  }
}

/** AI增强 */
async function handleAIEnhance(): Promise<void> {
  editorState.aiPanelVisible.value = true
}

/** 分享 */
function handleShare(): void {
  showShareDialog.value = true
}

async function confirmShare(): Promise<void> {
  if (noteId.value !== null) {
    await noteStore.shareNote(noteId.value)
  }
}

function copyShareLink(): void {
  if (noteStore.shareInfo?.share_url) {
    navigator.clipboard.writeText(noteStore.shareInfo.share_url)
    ElMessage.success('链接已复制')
  }
}

/** 返回列表 */
function goBack(): void {
  router.back()
}

/** 格式化日期 */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** 简易Markdown渲染 */
function renderMarkdown(text: string): string {
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/~~([^~]+)~~/g, '<del>$1</del>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/\n/g, '<br/>')
}

// 加载版本历史
watch(showVersionDialog, (visible: boolean) => {
  if (visible && noteId.value !== null) {
    noteStore.fetchVersions(noteId.value)
  }
})

onMounted(() => {
  if (noteId.value !== null) {
    noteStore.loadNote(noteId.value)
  }
})
</script>

<style lang="scss" scoped>
.note-edit {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;

  &__toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    border-bottom: 1px solid #e8e8e8;
    gap: 12px;
    flex-shrink: 0;
  }

  &__toolbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    min-width: 0;
  }

  &__toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  &__title-input {
    flex: 1;

    :deep(.el-input__inner) {
      font-size: 18px;
      font-weight: 600;
      border: none;
      background: transparent;
      padding: 0;
    }
  }

  &__body {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  &__editor {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  &__format-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    border-bottom: 1px solid #f0f0f0;
    background: #fafafa;
  }

  &__mode-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__content {
    flex: 1;
    overflow: hidden;
    position: relative;
  }

  &__textarea {
    width: 100%;
    height: 100%;
    padding: 20px;
    border: none;
    outline: none;
    resize: none;
    font-size: 15px;
    line-height: 1.8;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
    color: #303133;
    background: #fff;
  }

  &__preview {
    width: 100%;
    height: 100%;
    padding: 20px;
    overflow-y: auto;
    font-size: 15px;
    line-height: 1.8;

    :deep(h1), :deep(h2), :deep(h3) {
      margin: 16px 0 8px;
    }
    :deep(h1) { font-size: 24px; }
    :deep(h2) { font-size: 20px; }
    :deep(h3) { font-size: 17px; }
    :deep(pre) {
      background: #1e1e1e;
      color: #d4d4d4;
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
    }
    :deep(code) {
      font-family: 'Menlo', monospace;
      font-size: 13px;
    }
    :deep(li) {
      margin-left: 20px;
    }
  }

  &__ai-panel {
    width: 320px;
    border-left: 1px solid #e8e8e8;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    background: #fafafa;
  }

  &__ai-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #e8e8e8;

    h4 {
      margin: 0;
      font-size: 15px;
    }
  }

  &__ai-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
  }

  &__ai-result {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  &__ai-result-content {
    font-size: 14px;
    line-height: 1.6;
    color: #606266;

    ul {
      padding-left: 20px;
    }
    li {
      margin-bottom: 4px;
    }
  }

  &__status-bar {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 6px 16px;
    border-top: 1px solid #e8e8e8;
    font-size: 12px;
    color: #909399;
    background: #fafafa;
    flex-shrink: 0;
  }

  &__save-status {
    margin-left: auto;

    &--saving { color: #e6a23c; }
    &--saved { color: #67c23a; }
    &--error { color: #f56c6c; }
  }

  &__version-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__version-summary {
    color: #909399;
    font-size: 13px;
  }

  &__share-info {
    :deep(.el-input-group__append) {
      cursor: pointer;
    }
  }
}

@media (max-width: 768px) {
  .note-edit {
    &__ai-panel {
      display: none;
    }
    &__toolbar-right {
      .el-button span {
        display: none;
      }
    }
  }
}
</style>
