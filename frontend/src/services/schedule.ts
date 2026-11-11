/**
 * AI4Edu 个人课表 API
 * 场景仪表盘「导入课表」：上传 CSV/Excel → 今日课表与今日课程数随之更新
 */
import api from './api'

// ============ 类型定义 ============

/** 课表条目（一节课） */
export interface ScheduleItem {
  id: number
  name: string
  weekday: number
  weekday_label: string
  start_time: string
  end_time: string
  location: string
  teacher: string
  weeks: string
  note: string
  status: 'ongoing' | 'ended' | 'upcoming'
  source_file: string
}

/** 某天课程 */
export interface DaySchedule {
  date: string
  weekday: number
  weekday_label: string
  items: ScheduleItem[]
  count: number
  source: 'imported' | 'empty'
  updated_at?: string | null
}

/** 整周课表 */
export interface WeekSchedule {
  days: Array<{
    weekday: number
    label: string
    is_today: boolean
    count: number
    items: ScheduleItem[]
  }>
  total: number
  source_file: string
  updated_at?: string | null
}

/** 导入结果 */
export interface ScheduleImportResult {
  filename: string
  mode: 'replace' | 'append'
  /** true 表示这只是校验预览，尚未写库 */
  dry_run?: boolean
  total_rows: number
  imported: number
  skipped: number
  /** 校验通过、可写入的条数（dry_run 时有值） */
  valid?: number
  failed: number
  errors: Array<{ row: number; reasons: string[]; raw?: Record<string, string> }>
  errors_truncated: boolean
  today_count?: number
}

// ============ API 方法 ============

export const scheduleApi = {
  /** 某天课程（默认今天） */
  async getToday(day?: string): Promise<DaySchedule> {
    const res = (await api.get('/dashboard/schedule/today', {
      params: day ? { day } : {},
    })) as any
    return res.data as DaySchedule
  },

  /** 整周课表 */
  async getWeek(): Promise<WeekSchedule> {
    const res = (await api.get('/dashboard/schedule/week')) as any
    return res.data as WeekSchedule
  },

  /** 导入课表文件；dryRun=true 时只校验不写库 */
  async importFile(
    file: File,
    mode: 'replace' | 'append' = 'replace',
    dryRun = false,
  ): Promise<{ result: ScheduleImportResult; message: string }> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('mode', mode)
    formData.append('dry_run', String(dryRun))
    const res = (await api.post('/dashboard/schedule/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })) as any
    return { result: res.data as ScheduleImportResult, message: res.message || '' }
  },

  /** 清空我的课表 */
  async clear(): Promise<number> {
    const res = (await api.delete('/dashboard/schedule')) as any
    return res.data?.deleted ?? 0
  },

  /** 下载导入模板（浏览器直接下载） */
  async downloadTemplate(): Promise<void> {
    const res = (await api.get('/dashboard/schedule/template', {
      responseType: 'blob',
    })) as any
    // blob 响应经拦截器后可能直接是 Blob，也可能包在 data 里
    const raw: BlobPart = res?.data ?? res
    const blob = raw instanceof Blob ? raw : new Blob([raw], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '课表导入模板.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },
}

export default scheduleApi
