/**
 * 智慧学伴 笔记 Store
 * 管理笔记列表、当前笔记、版本历史、分享
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { noteApi, type NoteItem, type NoteDetail, type NoteVersion, type NoteShareInfo } from '@/services/note'
import { ElMessage } from 'element-plus'

export const useNoteStore = defineStore('note', () => {
  // ============ State ============

  /** 笔记列表 */
  const notes = ref<NoteItem[]>([])
  /** 当前笔记详情 */
  const currentNote = ref<NoteDetail | null>(null)
  /** 版本历史 */
  const versions = ref<NoteVersion[]>([])
  /** 分享信息 */
  const shareInfo = ref<NoteShareInfo | null>(null)
  /** 加载状态 */
  const isLoading = ref<boolean>(false)
  /** 笔记总数 */
  const totalNotes = ref<number>(0)
  /** 当前页码 */
  const currentPage = ref<number>(1)
  /** AI增强结果 */
  const aiEnhanceResult = ref<Record<string, unknown> | null>(null)
  /** AI增强加载状态 */
  const aiEnhanceLoading = ref<boolean>(false)

  // ============ Getters ============

  /** 是否有当前笔记 */
  const hasCurrentNote = computed<boolean>(() => currentNote.value !== null)

  /** 当前笔记标签 */
  const currentNoteTags = computed<string[]>(() => currentNote.value?.tags ?? [])

  /** 笔记是否已AI增强 */
  const isAiEnhanced = computed<boolean>(() => currentNote.value?.is_ai_enhanced ?? false)

  /** 笔记是否已分享 */
  const isShared = computed<boolean>(() => currentNote.value?.is_shared ?? false)

  // ============ Actions ============

  /**
   * 获取笔记列表
   * @param page 页码
   * @param pageSize 每页数量
   * @param params 筛选参数
   */
  async function fetchNotes(
    page: number = 1,
    pageSize: number = 20,
    params?: { note_type?: string; search?: string; course_id?: number }
  ): Promise<void> {
    isLoading.value = true
    try {
      const response = await noteApi.listNotes({
        page,
        page_size: pageSize,
        ...params,
      })
      notes.value = response.items
      totalNotes.value = response.total
      currentPage.value = page
    } catch (error) {
      console.error('获取笔记列表失败:', error)
      ElMessage.error('获取笔记列表失败')
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 创建笔记
   * @param params 创建参数
   */
  async function createNote(params: { title: string; content?: string; note_type?: string; tags?: string[]; course_id?: number }): Promise<NoteDetail | null> {
    try {
      const note = await noteApi.createNote(params)
      notes.value.unshift({
        id: note.id,
        title: note.title,
        content: note.content,
        summary: note.summary,
        note_type: note.note_type,
        tags: note.tags,
        course_id: note.course_id,
        is_ai_enhanced: note.is_ai_enhanced,
        is_shared: note.is_shared,
        version: note.version,
        created_at: note.created_at,
        updated_at: note.updated_at,
      })
      currentNote.value = note
      ElMessage.success('笔记创建成功')
      return note
    } catch (error) {
      console.error('创建笔记失败:', error)
      ElMessage.error('创建笔记失败')
      return null
    }
  }

  /**
   * 更新笔记
   * @param noteId 笔记ID
   * @param params 更新参数
   */
  async function updateNote(noteId: number, params: { title?: string; content?: string; tags?: string[] }): Promise<NoteDetail | null> {
    try {
      const note = await noteApi.updateNote(noteId, params)
      currentNote.value = note
      // 更新列表中的对应项
      const index = notes.value.findIndex((n) => n.id === noteId)
      if (index !== -1) {
        notes.value[index] = {
          id: note.id,
          title: note.title,
          content: note.content,
          summary: note.summary,
          note_type: note.note_type,
          tags: note.tags,
          course_id: note.course_id,
          is_ai_enhanced: note.is_ai_enhanced,
          is_shared: note.is_shared,
          version: note.version,
          created_at: note.created_at,
          updated_at: note.updated_at,
        }
      }
      return note
    } catch (error) {
      console.error('更新笔记失败:', error)
      ElMessage.error('保存笔记失败')
      return null
    }
  }

  /**
   * 删除笔记
   * @param noteId 笔记ID
   */
  async function deleteNote(noteId: number): Promise<void> {
    try {
      await noteApi.deleteNote(noteId)
      notes.value = notes.value.filter((n) => n.id !== noteId)
      if (currentNote.value?.id === noteId) {
        currentNote.value = null
      }
      ElMessage.success('笔记已删除')
    } catch (error) {
      console.error('删除笔记失败:', error)
      ElMessage.error('删除笔记失败')
    }
  }

  /**
   * AI增强笔记
   * @param noteId 笔记ID
   * @param enhanceType 增强类型
   */
  async function aiEnhance(noteId: number, enhanceType: 'summarize' | 'extract_points' | 'expand' | 'correct' | 'translate'): Promise<void> {
    aiEnhanceLoading.value = true
    try {
      const result = await noteApi.aiEnhance(noteId, { enhance_type: enhanceType })
      aiEnhanceResult.value = result
      // 刷新笔记详情
      const note = await noteApi.getNote(noteId)
      currentNote.value = note
      ElMessage.success('AI增强完成')
    } catch (error) {
      console.error('AI增强失败:', error)
      ElMessage.error('AI增强失败')
    } finally {
      aiEnhanceLoading.value = false
    }
  }

  /**
   * 获取版本历史
   * @param noteId 笔记ID
   */
  async function fetchVersions(noteId: number): Promise<void> {
    try {
      versions.value = await noteApi.listVersions(noteId)
    } catch (error) {
      console.error('获取版本历史失败:', error)
      ElMessage.error('获取版本历史失败')
    }
  }

  /**
   * 分享笔记
   * @param noteId 笔记ID
   * @param isPublic 是否公开
   * @param expiresInDays 过期天数
   */
  async function shareNote(noteId: number, isPublic: boolean = true, expiresInDays?: number): Promise<NoteShareInfo | null> {
    try {
      shareInfo.value = await noteApi.shareNote(noteId, { is_public: isPublic, expires_in_days: expiresInDays })
      // 更新分享状态
      if (currentNote.value?.id === noteId) {
        currentNote.value.is_shared = true
      }
      const noteItem = notes.value.find((n) => n.id === noteId)
      if (noteItem) {
        noteItem.is_shared = true
      }
      ElMessage.success('分享链接已生成')
      return shareInfo.value
    } catch (error) {
      console.error('分享笔记失败:', error)
      ElMessage.error('分享笔记失败')
      return null
    }
  }

  /**
   * 加载笔记详情
   * @param noteId 笔记ID
   */
  async function loadNote(noteId: number): Promise<void> {
    isLoading.value = true
    try {
      currentNote.value = await noteApi.getNote(noteId)
    } catch (error) {
      console.error('加载笔记详情失败:', error)
      ElMessage.error('加载笔记详情失败')
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 清除当前笔记
   */
  function clearCurrentNote(): void {
    currentNote.value = null
    versions.value = []
    shareInfo.value = null
    aiEnhanceResult.value = null
  }

  return {
    // State
    notes,
    currentNote,
    versions,
    shareInfo,
    isLoading,
    totalNotes,
    currentPage,
    aiEnhanceResult,
    aiEnhanceLoading,
    // Getters
    hasCurrentNote,
    currentNoteTags,
    isAiEnhanced,
    isShared,
    // Actions
    fetchNotes,
    createNote,
    updateNote,
    deleteNote,
    aiEnhance,
    fetchVersions,
    shareNote,
    loadNote,
    clearCurrentNote,
  }
})
