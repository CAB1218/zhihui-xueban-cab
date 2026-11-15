/**
 * 智慧学伴 笔记编辑器组合式函数
 * 管理编辑器状态、AI增强、自动保存、快捷键、Markdown切换
 */
import { ref, computed, watch, onMounted, onUnmounted, type Ref } from 'vue'
import { useNoteStore } from '@/stores/note'
import { ElMessage } from 'element-plus'

/** 编辑器模式 */
type EditorMode = 'markdown' | 'richtext'

/** 保存状态 */
type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export function useNoteEditor(noteId: Ref<number | null>) {
  const noteStore = useNoteStore()

  // ============ 编辑器状态 ============

  /** 编辑器内容 */
  const content = ref<string>('')
  /** 笔记标题 */
  const title = ref<string>('')
  /** 当前光标位置 */
  const cursorPosition = ref<number>(0)
  /** 选中文本 */
  const selectedText = ref<string>('')
  /** 编辑器模式 */
  const editorMode = ref<EditorMode>('markdown')
  /** 保存状态 */
  const saveStatus = ref<SaveStatus>('idle')
  /** 是否有未保存的修改 */
  const isDirty = ref<boolean>(false)
  /** 字数统计 */
  const wordCount = ref<number>(0)
  /** 字符统计 */
  const charCount = ref<number>(0)
  /** 当前版本号 */
  const currentVersion = ref<number>(1)
  /** AI增强面板是否可见 */
  const aiPanelVisible = ref<boolean>(false)
  /** 自动保存定时器 */
  let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
  /** 自动保存间隔（毫秒） */
  const AUTO_SAVE_DELAY = 3000

  // ============ 计算属性 ============

  /** 是否可以保存 */
  const canSave = computed<boolean>(() => isDirty.value && saveStatus.value !== 'saving')

  /** 保存状态文本 */
  const saveStatusText = computed<string>(() => {
    const statusMap: Record<SaveStatus, string> = {
      idle: '',
      saving: '保存中...',
      saved: '已保存',
      error: '保存失败',
    }
    return statusMap[saveStatus.value]
  })

  // ============ 内容监控 ============

  /** 监听内容变化，触发字数统计和自动保存 */
  watch(content, (newVal: string) => {
    updateWordCount(newVal)
    isDirty.value = true
    saveStatus.value = 'idle'
    scheduleAutoSave()
  })

  watch(title, () => {
    isDirty.value = true
    saveStatus.value = 'idle'
    scheduleAutoSave()
  })

  // ============ 方法 ============

  /**
   * 初始化编辑器
   */
  async function initEditor(): Promise<void> {
    if (noteId.value === null) return

    await noteStore.loadNote(noteId.value)
    const note = noteStore.currentNote
    if (note) {
      content.value = note.content || ''
      title.value = note.title || ''
      currentVersion.value = note.version || 1
      isDirty.value = false
      updateWordCount(content.value)
    }
  }

  /**
   * 更新字数统计
   * @param text 文本内容
   */
  function updateWordCount(text: string): void {
    charCount.value = text.length
    // 中文按字符计数，英文按空格分词
    const chineseChars = (text.match(/[\u4e00-\u9fff]/g) || []).length
    const englishWords = text.replace(/[\u4e00-\u9fff]/g, ' ').trim().split(/\s+/).filter(Boolean).length
    wordCount.value = chineseChars + englishWords
  }

  /**
   * 调度自动保存（debounce）
   */
  function scheduleAutoSave(): void {
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
    }
    autoSaveTimer = setTimeout(() => {
      saveNote()
    }, AUTO_SAVE_DELAY)
  }

  /**
   * 保存笔记
   */
  async function saveNote(): Promise<void> {
    if (noteId.value === null || !isDirty.value) return

    saveStatus.value = 'saving'
    try {
      const result = await noteStore.updateNote(noteId.value, {
        title: title.value,
        content: content.value,
      })
      if (result) {
        saveStatus.value = 'saved'
        isDirty.value = false
        currentVersion.value = result.version
        // 3秒后清除保存状态
        setTimeout(() => {
          if (saveStatus.value === 'saved') {
            saveStatus.value = 'idle'
          }
        }, 3000)
      } else {
        saveStatus.value = 'error'
      }
    } catch {
      saveStatus.value = 'error'
    }
  }

  /**
   * 手动保存（Ctrl+S）
   */
  async function manualSave(): Promise<void> {
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
      autoSaveTimer = null
    }
    await saveNote()
    if (saveStatus.value === 'saved') {
      ElMessage.success('保存成功')
    }
  }

  /**
   * AI增强笔记
   * @param enhanceType 增强类型
   */
  async function aiEnhance(enhanceType: 'summarize' | 'extract_points' | 'expand' | 'correct' | 'translate'): Promise<void> {
    if (noteId.value === null) return

    await noteStore.aiEnhance(noteId.value, enhanceType)
    // 根据增强类型更新内容
    const result = noteStore.aiEnhanceResult
    if (result) {
      if (enhanceType === 'summarize' && result.summary) {
        // 摘要不替换内容，显示在AI面板
      } else if (enhanceType === 'expand' && result.expanded_content) {
        content.value = result.expanded_content as string
      } else if (enhanceType === 'correct' && result.corrected_content) {
        content.value = result.corrected_content as string
      }
    }
  }

  /**
   * 切换编辑器模式
   */
  function toggleEditorMode(): void {
    editorMode.value = editorMode.value === 'markdown' ? 'richtext' : 'markdown'
  }

  /**
   * 处理选区变化
   * @param selectionStart 选区起点
   * @param selectionEnd 选区终点
   * @param text 完整文本
   */
  function handleSelectionChange(selectionStart: number, selectionEnd: number, text: string): void {
    cursorPosition.value = selectionStart
    selectedText.value = text.substring(selectionStart, selectionEnd)
  }

  /**
   * 在光标处插入文本
   * @param insertText 要插入的文本
   */
  function insertAtCursor(insertText: string): void {
    const before = content.value.substring(0, cursorPosition.value)
    const after = content.value.substring(cursorPosition.value)
    content.value = before + insertText + after
    cursorPosition.value += insertText.length
  }

  /**
   * 包裹选中文本
   * @param prefix 前缀
   * @param suffix 后缀
   */
  function wrapSelection(prefix: string, suffix: string): void {
    if (selectedText.value) {
      content.value = content.value.replace(
        selectedText.value,
        `${prefix}${selectedText.value}${suffix}`
      )
    } else {
      content.value = `${content.value.substring(0, cursorPosition.value)}${prefix}${suffix}${content.value.substring(cursorPosition.value)}`
      cursorPosition.value += prefix.length
    }
  }

  /**
   * 撤销到指定版本
   * @param version 版本号
   */
  async function revertToVersion(version: number): Promise<void> {
    if (noteId.value === null) return

    const targetVersion = noteStore.versions.find((v) => v.version === version)
    if (targetVersion) {
      content.value = targetVersion.content
      isDirty.value = true
      ElMessage.success(`已回退到版本 ${version}`)
    }
  }

  // ============ 快捷键 ============

  /**
   * 键盘事件处理
   */
  function handleKeydown(event: KeyboardEvent): void {
    // Ctrl+S / Cmd+S 保存
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
      event.preventDefault()
      manualSave()
      return
    }
    // Ctrl+B 粗体
    if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
      event.preventDefault()
      wrapSelection('**', '**')
      return
    }
    // Ctrl+I 斜体
    if ((event.ctrlKey || event.metaKey) && event.key === 'i') {
      event.preventDefault()
      wrapSelection('*', '*')
      return
    }
    // Ctrl+K 链接
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
      event.preventDefault()
      wrapSelection('[', '](url)')
      return
    }
  }

  // ============ 生命周期 ============

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
    initEditor()
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeydown)
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
      // 离开页面前保存
      if (isDirty.value) {
        saveNote()
      }
    }
  })

  return {
    // State
    content,
    title,
    cursorPosition,
    selectedText,
    editorMode,
    saveStatus,
    isDirty,
    wordCount,
    charCount,
    currentVersion,
    aiPanelVisible,
    // Computed
    canSave,
    saveStatusText,
    // Methods
    initEditor,
    saveNote,
    manualSave,
    aiEnhance,
    toggleEditorMode,
    handleSelectionChange,
    insertAtCursor,
    wrapSelection,
    revertToVersion,
    handleKeydown,
  }
}
