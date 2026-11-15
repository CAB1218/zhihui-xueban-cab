/**
 * 智慧学伴 离线操作队列
 * 管理离线期间的 API 写操作（POST/PUT/DELETE），
 * 网络恢复后自动重试同步
 *
 * 数据流：
 * 1. 离线时调用 enqueue() 将操作存入 IndexedDB
 * 2. 网络恢复时调用 processQueue() 逐条重试
 * 3. 同步成功的条目从队列中移除
 * 4. 同步失败的条目保留，等待下次重试
 */
import { openDB, type IDBPDatabase, type DBSchema } from 'idb'

/** 队列操作条目 */
interface QueueEntry {
  /** 自增主键 */
  id?: number
  /** 请求 URL */
  url: string
  /** HTTP 方法 */
  method: 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  /** 请求头（JSON 序列化） */
  headers: Record<string, string>
  /** 请求体（JSON 字符串） */
  body: string | null
  /** 入队时间 */
  createdAt: string
  /** 重试次数 */
  retryCount: number
  /** 上次重试时间 */
  lastRetryAt: string | null
  /** 操作类型标识（用于分类显示） */
  tag: string
}

/** 同步结果 */
interface SyncResult {
  /** 总条目数 */
  total: number
  /** 同步成功数 */
  succeeded: number
  /** 同步失败数 */
  failed: number
  /** 失败的条目 ID 列表 */
  failedIds: number[]
}

/** IndexedDB Schema */
interface OfflineQueueDBSchema extends DBSchema {
  operations: {
    key: number
    value: QueueEntry
    indexes: {
      'by-tag': string
      'by-created': string
    }
  }
}

/** 数据库名称 */
const DB_NAME = 'ai4edu-offline-queue'

/** 数据库版本 */
const DB_VERSION = 1

/** 最大重试次数 */
const MAX_RETRY_COUNT = 5

/** 数据库实例缓存 */
let dbInstance: IDBPDatabase<OfflineQueueDBSchema> | null = null

/**
 * 获取 IndexedDB 实例（单例模式）
 *
 * @returns IDBPDatabase 实例
 */
async function getDB(): Promise<IDBPDatabase<OfflineQueueDBSchema>> {
  if (dbInstance) return dbInstance

  dbInstance = await openDB<OfflineQueueDBSchema>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('operations')) {
        const store = db.createObjectStore('operations', {
          keyPath: 'id',
          autoIncrement: true,
        })
        store.createIndex('by-tag', 'tag')
        store.createIndex('by-created', 'createdAt')
      }
    },
  })

  return dbInstance
}

/**
 * 将离线操作加入队列
 *
 * @param url - 请求 URL
 * @param method - HTTP 方法
 * @param body - 请求体（将序列化为 JSON）
 * @param tag - 操作类型标签（如 'note', 'question', 'lesson_plan'）
 * @param headers - 额外请求头
 * @returns 队列条目 ID
 */
export async function enqueue(
  url: string,
  method: 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  body: unknown = null,
  tag: string = 'general',
  headers: Record<string, string> = { 'Content-Type': 'application/json' }
): Promise<number> {
  const db = await getDB()
  const now = new Date().toISOString()

  const entry: QueueEntry = {
    url,
    method,
    headers,
    body: body !== null ? JSON.stringify(body) : null,
    createdAt: now,
    retryCount: 0,
    lastRetryAt: null,
    tag,
  }

  const id = await db.add('operations', entry)
  console.log(`[OfflineQueue] Enqueued ${method} ${url} (id=${id}, tag=${tag})`)
  return id as number
}

/**
 * 处理队列中所有待同步的操作
 * 逐条发送请求，成功后从队列移除，失败则递增重试计数
 *
 * @returns 同步结果统计
 */
export async function processQueue(): Promise<SyncResult> {
  const db = await getDB()
  const allEntries = await db.getAll('operations')

  if (allEntries.length === 0) {
    return { total: 0, succeeded: 0, failed: 0, failedIds: [] }
  }

  let succeeded = 0
  let failed = 0
  const failedIds: number[] = []

  for (const entry of allEntries) {
    // 超过最大重试次数则跳过
    if (entry.retryCount >= MAX_RETRY_COUNT) {
      console.warn(
        `[OfflineQueue] Entry ${entry.id} exceeded max retries (${MAX_RETRY_COUNT}), removing`
      )
      await db.delete('operations', entry.id!)
      failedIds.push(entry.id!)
      failed++
      continue
    }

    try {
      const fetchOptions: RequestInit = {
        method: entry.method,
        headers: entry.headers,
      }

      if (entry.body !== null) {
        fetchOptions.body = entry.body
      }

      const response = await fetch(entry.url, fetchOptions)

      if (response.ok) {
        // 同步成功，移除条目
        await db.delete('operations', entry.id!)
        succeeded++
        console.log(`[OfflineQueue] Synced ${entry.method} ${entry.url} (id=${entry.id})`)
      } else {
        // 服务端返回错误，增加重试计数
        entry.retryCount++
        entry.lastRetryAt = new Date().toISOString()
        await db.put('operations', entry)
        failedIds.push(entry.id!)
        failed++
        console.warn(
          `[OfflineQueue] Sync failed for ${entry.method} ${entry.url} (status=${response.status}, retry=${entry.retryCount})`
        )
      }
    } catch (error) {
      // 网络错误，增加重试计数
      entry.retryCount++
      entry.lastRetryAt = new Date().toISOString()
      await db.put('operations', entry)
      failedIds.push(entry.id!)
      failed++
      console.error(`[OfflineQueue] Sync error for ${entry.method} ${entry.url}:`, error)
    }
  }

  const result: SyncResult = {
    total: allEntries.length,
    succeeded,
    failed,
    failedIds,
  }

  console.log(
    `[OfflineQueue] Process complete: ${succeeded}/${allEntries.length} succeeded`
  )

  return result
}

/**
 * 获取队列中待处理的操作数量
 *
 * @returns 待处理数量
 */
export async function getPendingCount(): Promise<number> {
  const db = await getDB()
  return db.count('operations')
}

/**
 * 获取队列中所有待处理的操作
 *
 * @returns 队列条目列表
 */
export async function getPendingEntries(): Promise<QueueEntry[]> {
  const db = await getDB()
  return db.getAll('operations')
}

/**
 * 按标签获取待处理的操作
 *
 * @param tag - 操作类型标签
 * @returns 匹配的队列条目列表
 */
export async function getPendingByTag(tag: string): Promise<QueueEntry[]> {
  const db = await getDB()
  const index = db.transaction('operations').store.index('by-tag')
  return index.getAll(tag)
}

/**
 * 删除队列中的指定操作
 *
 * @param id - 操作 ID
 */
export async function removeEntry(id: number): Promise<void> {
  const db = await getDB()
  await db.delete('operations', id)
}

/**
 * 清空整个队列
 */
export async function clearQueue(): Promise<void> {
  const db = await getDB()
  await db.clear('operations')
}

/**
 * 清理超过最大重试次数的失败条目
 *
 * @returns 清理的条目数
 */
export async function cleanupFailedEntries(): Promise<number> {
  const db = await getDB()
  const allEntries = await db.getAll('operations')
  let cleaned = 0

  for (const entry of allEntries) {
    if (entry.retryCount >= MAX_RETRY_COUNT) {
      await db.delete('operations', entry.id!)
      cleaned++
    }
  }

  return cleaned
}

/**
 * 获取队列统计信息
 *
 * @returns 各标签的待处理数量
 */
export async function getQueueStats(): Promise<Record<string, number>> {
  const db = await getDB()
  const allEntries = await db.getAll('operations')
  const stats: Record<string, number> = {}

  for (const entry of allEntries) {
    stats[entry.tag] = (stats[entry.tag] || 0) + 1
  }

  stats['total'] = allEntries.length
  return stats
}

/**
 * 发送请求的离线安全包装器
 * 在线时直接发送请求，离线时自动存入队列
 *
 * @param url - 请求 URL
 * @param method - HTTP 方法
 * @param body - 请求体
 * @param tag - 操作类型标签
 * @param headers - 额外请求头
 * @returns 响应对象（在线时为真实响应，离线时为模拟的 202 响应）
 */
export async function safeRequest(
  url: string,
  method: 'POST' | 'PUT' | 'DELETE' | 'PATCH',
  body: unknown = null,
  tag: string = 'general',
  headers: Record<string, string> = { 'Content-Type': 'application/json' }
): Promise<Response> {
  if (navigator.onLine) {
    // 在线：直接发送请求
    const fetchOptions: RequestInit = {
      method,
      headers,
    }
    if (body !== null) {
      fetchOptions.body = JSON.stringify(body)
    }
    return fetch(url, fetchOptions)
  }

  // 离线：存入队列，返回模拟响应
  await enqueue(url, method, body, tag, headers)

  return new Response(
    JSON.stringify({
      code: 202,
      message: '操作已暂存，将在网络恢复后同步',
      data: null,
    }),
    {
      status: 202,
      headers: { 'Content-Type': 'application/json' },
    }
  )
}
