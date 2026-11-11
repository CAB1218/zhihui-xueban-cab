/**
 * 文件导入对话框的公共契约
 * 学情分析（成绩/答题记录）、课程梳理（大纲/课表）共用同一套交互
 */

/** 未通过校验的行 */
export interface ImportIssue {
  row: number
  reasons: string[]
  raw?: Record<string, unknown>
}

/** 结果摘要里的一小段文字，tone 决定颜色 */
export interface ImportSummaryPart {
  text: string
  tone?: 'ok' | 'warn' | 'bad' | 'muted'
}

/** 上传后要展示给用户的结果 */
export interface ImportDialogResult {
  /** 结果标题，如「成功导入 12 条记录」 */
  title: string
  /** 标题语气 */
  tone?: 'success' | 'warning' | 'error' | 'info'
  /** 摘要：文件共 N 行 / 成功 N 条 / 失败 N 行 */
  summary?: ImportSummaryPart[]
  /** 未通过校验的行 */
  errors?: ImportIssue[]
  errorsTruncated?: boolean
  /** 交回给调用方的原始数据，用于刷新页面或定位新记录 */
  payload?: unknown
}

/** 字段说明表 */
export interface ImportFieldRow {
  field: string
  required: string
  desc: string
}

/** 上传函数：给一个文件，返回展示结果 */
export type ImportSubmit = (file: File) => Promise<ImportDialogResult>
