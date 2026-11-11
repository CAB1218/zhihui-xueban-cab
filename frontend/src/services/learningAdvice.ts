/**
 * 个性化学习建议服务（任务3）
 * 对应后端 /learning-advice/*
 */
import api from './api'

export interface AdviceCourse {
  id: number
  name: string
  subject?: string
}

export interface AdviceStudent {
  student_id: number
  name: string
  grade?: string | null
  record_count: number
  judgeable_count: number
  accuracy: number | null
  sufficient: boolean
}

export interface PlanMaterial {
  kind: 'textbook' | 'resource' | 'rule' | string
  title: string
  detail?: string
  source?: string
  rule?: string
  resource_id?: number
  resource_type?: string
  for?: string
  order?: number
}

export interface PlanPractice {
  stage: string
  count: number
  desc: string
  pass_line: string
}

export interface PlanItem {
  order: number
  knowledge_point: string
  status: string
  status_label: string
  accuracy: number | null
  problem: string
  evidence: {
    attempts?: number
    correct_count?: number
    accuracy?: number | null
    record_ids?: number[]
    text?: string
  }
  goal: string
  goal_level: string
  outline: {
    matched: boolean
    unit?: string | null
    unit_index?: number | null
    content_index?: number | null
    topics: string[]
    requirements: string[]
    textbook_ref?: string | null
    hours?: number
  }
  content: string[]
  practices: PlanPractice[]
  activity: string
  materials: PlanMaterial[]
  reason: string
  prerequisites: Array<{ from_topic: string; to_topic: string; description: string }>
  order_reason: string
  estimated_minutes: number
  acceptance: string
  teacher_tip: string
  adjustable?: string[]
}

export interface ObservationItem {
  knowledge_point: string
  evidence: string
  action: string
  decision_rule: string
  reason: string
}

export interface ScheduleDay {
  day: number
  item_orders: number[]
  knowledge_points: string[]
  minutes: number
  note: string
}

export interface LearningPlan {
  plan_id: number | null
  student: { id: number; name: string; grade?: string | null; major?: string | null }
  course: { id: number | null; name: string; subject?: string | null }
  duration_days: number
  focus?: string | null
  engine: string
  generated_at: string
  summary: {
    accuracy: number | null
    attempts: number
    records_valid?: number
    weak_count: number
    fair_count: number
    insufficient_count: number
    student_evidence_sufficient: boolean
  }
  goal_overview: string
  items: PlanItem[]
  observation_items: ObservationItem[]
  schedule: ScheduleDay[]
  teacher_notes: string[]
  data_notes: string[]
  materials_index: PlanMaterial[]
  outline: {
    available: boolean
    outline_id?: number
    title?: string
    course_query?: string
    generated_at?: string
  }
  resources_checked?: number
  thresholds?: { min_attempts: number; acc_good: number; acc_weak: number }
}

export interface PlanBrief {
  id: number
  student_id: number
  student_name?: string
  course_id?: number
  course_name?: string
  title?: string
  duration_days: number
  focus?: string | null
  engine?: string
  created_at?: string
}

export interface StudentImportResult {
  total: number
  created: number
  skipped: number
  failed: number
  created_rows: Array<{ row: number; name: string; email: string }>
  skipped_rows: Array<{ row: number; name: string; reason: string }>
  errors: Array<{ row: number; reasons: string[]; raw?: Record<string, unknown> }>
  default_password?: string | null
}

export const learningAdviceApi = {
  async courses(): Promise<AdviceCourse[]> {
    const res: any = await api.get('/learning-advice/courses')
    return (res.data ?? []) as AdviceCourse[]
  },

  async students(courseId?: number): Promise<AdviceStudent[]> {
    const res: any = await api.get('/learning-advice/students', {
      params: courseId ? { course_id: courseId } : {},
    })
    return (res.data ?? []) as AdviceStudent[]
  },

  async generate(payload: {
    student_id: number
    course_id?: number
    duration_days?: number
    focus?: string
  }): Promise<LearningPlan> {
    const res: any = await api.post('/learning-advice/generate', payload, { timeout: 60000 })
    return res.data as LearningPlan
  },

  async plans(studentId?: number): Promise<PlanBrief[]> {
    const res: any = await api.get('/learning-advice/plans', {
      params: studentId ? { student_id: studentId } : {},
    })
    return (res.data ?? []) as PlanBrief[]
  },

  async plan(planId: number): Promise<LearningPlan> {
    const res: any = await api.get(`/learning-advice/plans/${planId}`)
    return res.data as LearningPlan
  },

  async remove(planId: number): Promise<void> {
    await api.delete(`/learning-advice/plans/${planId}`)
  },

  /** 下载 Markdown（带 token，不能直接 a.href） */
  async downloadPlan(planId: number, filename: string): Promise<void> {
    const res: any = await api.get(`/learning-advice/plans/${planId}/export`, {
      responseType: 'blob',
    })
    const raw: BlobPart = res?.data ?? res
    const blob = raw instanceof Blob ? raw : new Blob([raw], { type: 'text/markdown;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename.endsWith('.md') ? filename : `${filename}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },

  async importStudents(file: File): Promise<StudentImportResult> {
    const formData = new FormData()
    formData.append('file', file)
    const res: any = await api.post('/learning-advice/students/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
    return res.data as StudentImportResult
  },

  async downloadStudentTemplate(): Promise<void> {
    const res: any = await api.get('/learning-advice/students/import/template', {
      responseType: 'blob',
    })
    const raw: BlobPart = res?.data ?? res
    const blob = raw instanceof Blob ? raw : new Blob([raw], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '学生名单导入模板.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },
}
