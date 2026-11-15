/**
 * 智慧学伴 IndexedDB 离线存储工具
 * 封装 idb 库，提供离线笔记、对话缓存、草稿保存等功能
 */
import { openDB, type IDBPDatabase, type DBSchema } from 'idb'

/** 离线笔记记录 */
interface OfflineNote {
  id?: number
  title: string
  content: string
  note_type: string
  tags: string[]
  synced: boolean
  created_at: string
  updated_at: string
}

/** 离线AI对话缓存 */
interface ChatCache {
  id?: number
  session_id: string
  messages: Array<{
    role: string
    content: string
    timestamp: string
  }>
  scene: string
  created_at: string
  updated_at: string
}

/** 草稿记录 */
interface Draft {
  id?: number
  type: 'note' | 'question' | 'lesson_plan' | 'diagnosis'
  title: string
  content: string
  metadata: Record<string, unknown>
  auto_saved: boolean
  created_at: string
  updated_at: string
}

/** IndexedDB Schema 定义 */
interface AI4EduDBSchema extends DBSchema {
  offline_notes: {
    key: number
    value: OfflineNote
    indexes: {
      'by-synced': number
      'by-updated': string
    }
  }
  chat_cache: {
    key: number
    value: ChatCache
    indexes: {
      'by-session': string
      'by-updated': string
    }
  }
  drafts: {
    key: number
    value: Draft
    indexes: {
      'by-type': string
      'by-updated': string
    }
  }
}

/** 数据库名称 */
const DB_NAME = 'ai4edu-offline'

/** 数据库版本 */
const DB_VERSION = 1

/** 数据库实例缓存 */
let dbInstance: IDBPDatabase<AI4EduDBSchema> | null = null

/**
 * 获取 IndexedDB 实例（单例模式）
 *
 * @returns IDBPDatabase 实例
 */
async function getDB(): Promise<IDBPDatabase<AI4EduDBSchema>> {
  if (dbInstance) return dbInstance

  dbInstance = await openDB<AI4EduDBSchema>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // 离线笔记存储
      if (!db.objectStoreNames.contains('offline_notes')) {
        const noteStore = db.createObjectStore('offline_notes', {
          keyPath: 'id',
          autoIncrement: true,
        })
        noteStore.createIndex('by-synced', 'synced')
        noteStore.createIndex('by-updated', 'updated_at')
      }

      // AI对话缓存
      if (!db.objectStoreNames.contains('chat_cache')) {
        const chatStore = db.createObjectStore('chat_cache', {
          keyPath: 'id',
          autoIncrement: true,
        })
        chatStore.createIndex('by-session', 'session_id')
        chatStore.createIndex('by-updated', 'updated_at')
      }

      // 草稿存储
      if (!db.objectStoreNames.contains('drafts')) {
        const draftStore = db.createObjectStore('drafts', {
          keyPath: 'id',
          autoIncrement: true,
        })
        draftStore.createIndex('by-type', 'type')
        draftStore.createIndex('by-updated', 'updated_at')
      }
    },
  })

  return dbInstance
}

// ============ 草稿操作 ============

/**
 * 保存草稿（自动保存/手动保存）
 *
 * @param type - 草稿类型
 * @param title - 草稿标题
 * @param content - 草稿内容
 * @param metadata - 附加元数据
 * @param autoSaved - 是否为自动保存
 * @returns 保存后的草稿ID
 */
export async function saveDraft(
  type: Draft['type'],
  title: string,
  content: string,
  metadata: Record<string, unknown> = {},
  autoSaved: boolean = true
): Promise<number> {
  const db = await getDB()
  const now = new Date().toISOString()

  const draft: Draft = {
    type,
    title,
    content,
    metadata,
    auto_saved: autoSaved,
    created_at: now,
    updated_at: now,
  }

  const id = await db.add('drafts', draft)
  return id as number
}

/**
 * 更新已有草稿
 *
 * @param id - 草稿ID
 * @param updates - 更新字段
 */
export async function updateDraft(
  id: number,
  updates: Partial<Pick<Draft, 'title' | 'content' | 'metadata'>>
): Promise<void> {
  const db = await getDB()
  const existing = await db.get('drafts', id)
  if (!existing) return

  const updated: Draft = {
    ...existing,
    ...updates,
    updated_at: new Date().toISOString(),
  }

  await db.put('drafts', updated)
}

/**
 * 获取所有草稿
 *
 * @param type - 可选，按类型筛选
 * @returns 草稿列表
 */
export async function getDrafts(type?: Draft['type']): Promise<Draft[]> {
  const db = await getDB()

  if (type) {
    const index = db.transaction('drafts').store.index('by-type')
    return index.getAll(type)
  }

  return db.getAll('drafts')
}

/**
 * 获取单个草稿
 *
 * @param id - 草稿ID
 * @returns 草稿数据或undefined
 */
export async function getDraft(id: number): Promise<Draft | undefined> {
  const db = await getDB()
  return db.get('drafts', id)
}

/**
 * 删除草稿
 *
 * @param id - 草稿ID
 */
export async function deleteDraft(id: number): Promise<void> {
  const db = await getDB()
  await db.delete('drafts', id)
}

/**
 * 清理过期的自动保存草稿
 *
 * @param maxAgeMs - 最大保留时间（毫秒），默认7天
 */
export async function cleanupOldDrafts(maxAgeMs: number = 7 * 24 * 60 * 60 * 1000): Promise<void> {
  const db = await getDB()
  const cutoff = new Date(Date.now() - maxAgeMs).toISOString()
  const allDrafts = await db.getAll('drafts')

  const tx = db.transaction('drafts', 'readwrite')
  for (const draft of allDrafts) {
    if (draft.auto_saved && draft.updated_at < cutoff) {
      await tx.store.delete(draft.id!)
    }
  }
}

// ============ 离线笔记操作 ============

/**
 * 保存离线笔记
 *
 * @param title - 笔记标题
 * @param content - 笔记内容
 * @param noteType - 笔记类型
 * @param tags - 标签列表
 * @returns 保存后的笔记ID
 */
export async function saveOfflineNote(
  title: string,
  content: string,
  noteType: string = 'personal',
  tags: string[] = []
): Promise<number> {
  const db = await getDB()
  const now = new Date().toISOString()

  const note: OfflineNote = {
    title,
    content,
    note_type: noteType,
    tags,
    synced: false,
    created_at: now,
    updated_at: now,
  }

  const id = await db.add('offline_notes', note)
  return id as number
}

/**
 * 同步离线笔记到服务器
 *
 * 遍历所有未同步的笔记，尝试发送到服务端API
 * 成功后标记为已同步
 *
 * @returns 同步结果统计
 */
export async function syncOfflineNotes(): Promise<{
  total: number
  synced: number
  failed: number
}> {
  const db = await getDB()
  const index = db.transaction('offline_notes').store.index('by-synced')
  const unsyncedNotes = await index.getAll(0) // synced = false (0)

  let synced = 0
  let failed = 0

  for (const note of unsyncedNotes) {
    try {
      const accessToken = localStorage.getItem('access_token')
      const response = await fetch('/api/v1/notes/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({
          title: note.title,
          content: note.content,
          note_type: note.note_type,
          tags: note.tags,
        }),
      })

      if (response.ok) {
        // 标记为已同步
        note.synced = true
        note.updated_at = new Date().toISOString()
        await db.put('offline_notes', note)
        synced++
      } else {
        failed++
      }
    } catch (error) {
      console.error('[Storage] Failed to sync note:', note.id, error)
      failed++
    }
  }

  return {
    total: unsyncedNotes.length,
    synced,
    failed,
  }
}

/**
 * 获取所有离线笔记
 *
 * @param syncedOnly - 是否只获取已同步的笔记
 * @returns 笔记列表
 */
export async function getOfflineNotes(syncedOnly: boolean = false): Promise<OfflineNote[]> {
  const db = await getDB()
  const index = db.transaction('offline_notes').store.index('by-synced')

  if (syncedOnly) {
    return index.getAll(1) // synced = true (1)
  }

  return db.getAll('offline_notes')
}

/**
 * 删除离线笔记
 *
 * @param id - 笔记ID
 */
export async function deleteOfflineNote(id: number): Promise<void> {
  const db = await getDB()
  await db.delete('offline_notes', id)
}

// ============ AI对话缓存操作 ============

/**
 * 保存AI对话缓存
 *
 * @param sessionId - 会话ID
 * @param messages - 消息列表
 * @param scene - 场景标识
 * @returns 缓存ID
 */
export async function saveChatCache(
  sessionId: string,
  messages: Array<{ role: string; content: string; timestamp: string }>,
  scene: string = 'classroom'
): Promise<number> {
  const db = await getDB()
  const now = new Date().toISOString()

  // 查找已有缓存
  const index = db.transaction('chat_cache').store.index('by-session')
  const existing = await index.getAll(sessionId)

  if (existing.length > 0) {
    // 更新已有缓存
    const cache = existing[0]
    cache.messages = messages
    cache.scene = scene
    cache.updated_at = now
    await db.put('chat_cache', cache)
    return cache.id as number
  }

  // 新建缓存
  const cache: ChatCache = {
    session_id: sessionId,
    messages,
    scene,
    created_at: now,
    updated_at: now,
  }

  const id = await db.add('chat_cache', cache)
  return id as number
}

/**
 * 获取AI对话缓存
 *
 * @param sessionId - 会话ID
 * @returns 对话缓存或undefined
 */
export async function getChatCache(
  sessionId: string
): Promise<ChatCache | undefined> {
  const db = await getDB()
  const index = db.transaction('chat_cache').store.index('by-session')
  const results = await index.getAll(sessionId)
  return results[0]
}

/**
 * 删除AI对话缓存
 *
 * @param sessionId - 会话ID
 */
export async function deleteChatCache(sessionId: string): Promise<void> {
  const db = await getDB()
  // First, find matching records using a readonly transaction
  const readTx = db.transaction('chat_cache', 'readonly')
  const readIndex = readTx.store.index('by-session')
  const results = await readIndex.getAll(sessionId)

  // Then delete them using a readwrite transaction
  const writeTx = db.transaction('chat_cache', 'readwrite')
  for (const cache of results) {
    if (cache.id) {
      await writeTx.store.delete(cache.id)
    }
  }
}

/**
 * 清理过期的对话缓存
 *
 * @param maxAgeMs - 最大保留时间（毫秒），默认3天
 */
export async function cleanupOldChatCache(
  maxAgeMs: number = 3 * 24 * 60 * 60 * 1000
): Promise<void> {
  const db = await getDB()
  const cutoff = new Date(Date.now() - maxAgeMs).toISOString()
  const allCaches = await db.getAll('chat_cache')

  const tx = db.transaction('chat_cache', 'readwrite')
  for (const cache of allCaches) {
    if (cache.updated_at < cutoff) {
      await tx.store.delete(cache.id!)
    }
  }
}

// ============ 通用工具 ============

/**
 * 获取存储使用统计
 *
 * @returns 各存储的记录数
 */
export async function getStorageStats(): Promise<{
  offlineNotes: number
  unsyncedNotes: number
  chatCaches: number
  drafts: number
}> {
  const db = await getDB()

  const [allNotes, unsyncedNotes, allChats, allDrafts] = await Promise.all([
    db.count('offline_notes'),
    db.countFromIndex('offline_notes', 'by-synced', IDBKeyRange.only(0)),
    db.count('chat_cache'),
    db.count('drafts'),
  ])

  return {
    offlineNotes: allNotes,
    unsyncedNotes: unsyncedNotes,
    chatCaches: allChats,
    drafts: allDrafts,
  }
}

/**
 * 清除所有离线数据
 */
export async function clearAllOfflineData(): Promise<void> {
  const db = await getDB()
  const tx = db.transaction(['offline_notes', 'chat_cache', 'drafts'], 'readwrite')
  await Promise.all([
    tx.objectStore('offline_notes').clear(),
    tx.objectStore('chat_cache').clear(),
    tx.objectStore('drafts').clear(),
  ])
}
