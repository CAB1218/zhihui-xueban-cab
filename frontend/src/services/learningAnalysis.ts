/**
 * 学情分析 API
 * 模拟学情数据的整理与质量检查 → 个体/群体学习情况摘要
 */
import api from './api'

export interface QualityIssue {
  type: 'missing' | 'abnormal' | 'duplicate'
  code: string
  title: string
  count: number
  record_ids: number[]
  detail: string
  handling: string
  handling_type: string
}

export interface QualityStep {
  step: string
  before: number
  after: number
  removed: number
}

export interface Overview {
  course: { id?: number; name?: string; grade?: string }
  records_total: number
  records_valid: number
  records_excluded: number
  judgeable: number
  accuracy: number | null
  students: number
  courses: number
  date_from: string | null
  date_to: string | null
  record_type_distribution: Record<string, number>
  quality_counts: { missing: number; abnormal: number; duplicate: number }
  is_simulated: boolean
  simulated_count: number
}

export interface QualityResult {
  raw_count: number
  valid_count: number
  removed_count: number
  counts: { missing: number; abnormal: number; duplicate: number }
  issues: QualityIssue[]
  steps: QualityStep[]
  notes: string[]
}

export interface StudentBrief {
  student_id: number
  name: string
  grade?: string | null
  major?: string | null
  record_count: number
  judgeable_count: number
  accuracy: number | null
  courses: number[]
}

export interface KnowledgeRow {
  knowledge_point: string
  attempts: number
  correct_count: number
  accuracy: number
  status: 'good' | 'fair' | 'needs_work' | 'insufficient'
  status_label: string
  evidence_record_ids: number[]
  evidence_text: string
}

export interface IndividualReport {
  student: { id: number; name: string; grade?: string; major?: string; email?: string }
  course_name?: string
  overall: {
    records_total: number
    records_valid: number
    attempts: number
    correct_count: number
    accuracy: number | null
    accuracy_basis: string
    knowledge_point_count: number
    practice_days: number
    record_type_distribution: Record<string, number>
    avg_duration_minutes: number | null
  }
  knowledge_points: KnowledgeRow[]
  needs_consolidation: KnowledgeRow[]
  fair_areas: KnowledgeRow[]
  strengths: KnowledgeRow[]
  insufficient_evidence: KnowledgeRow[]
  data_notes: string[]
  thresholds: { min_attempts: number; acc_good: number; acc_weak: number }
  quality?: QualityResult
}

export interface CommonWeak {
  knowledge_point: string
  students_practiced: number
  attempts: number
  accuracy: number
  weak_students: number
  weak_ratio: number
  is_common_weak: boolean
  weak_student_names?: string[]
  evidence_text: string
}

export interface GroupReport {
  course: { id?: number; name?: string; grade?: string }
  cohort: {
    students_total: number
    students_judged: number
    students_reliable: number
    students_sparse: number
    total_attempts: number
    records_total: number
    records_valid: number
    avg_attempts: number
  }
  overall: { accuracy: number | null }
  knowledge_points: Array<{
    knowledge_point: string
    students_practiced: number
    attempts: number
    accuracy: number
    weak_students: number
    weak_ratio: number
    is_common_weak: boolean
  }>
  common_weak_points: CommonWeak[]
  student_stats: Array<{
    student_id: number
    name: string
    attempts: number
    correct_count: number
    accuracy: number | null
    knowledge_points_practiced?: number
    reliable_kp_count?: number
  }>
  differences: {
    accuracy?: {
      min: number
      max: number
      avg: number
      median: number
      std: number
      gap: number
      compared_students: number
      evidence_text: string
    }
    attempts?: { min: number; max: number; avg: number; evidence_text: string }
  }
  notable_cases: Array<{
    type: string
    student_id: number
    student_name: string
    note: string
  }>
  dimension_check: Array<{
    dimension: string
    available_ratio: number
    usable: boolean
    note: string
  }>
  data_notes: string[]
  thresholds: { min_attempts: number; acc_weak: number; common_weak_ratio: number }
  quality?: QualityResult
}

export const learningAnalysisApi = {
  async overview(courseId?: number): Promise<Overview> {
    const res = await api.get('/learning-analysis/overview', {
      params: courseId ? { course_id: courseId } : {},
    })
    return (res as any).data ?? res
  },

  async quality(courseId?: number): Promise<QualityResult> {
    const res = await api.get('/learning-analysis/quality', {
      params: courseId ? { course_id: courseId } : {},
    })
    return (res as any).data ?? res
  },

  async students(): Promise<StudentBrief[]> {
    const res = await api.get('/learning-analysis/students')
    return (res as any).data ?? res
  },

  async individual(studentId: number, courseId?: number): Promise<IndividualReport> {
    const res = await api.get(`/learning-analysis/individual/${studentId}`, {
      params: courseId ? { course_id: courseId } : {},
    })
    return (res as any).data ?? res
  },

  async group(courseId?: number): Promise<GroupReport> {
    const res = await api.get('/learning-analysis/group', {
      params: courseId ? { course_id: courseId } : {},
    })
    return (res as any).data ?? res
  },

  /** 导出报告，返回 Blob 供前端下载 */
  async exportReport(params: {
    kind: 'group' | 'individual'
    courseId?: number
    studentId?: number
    format: 'md' | 'docx'
  }): Promise<Blob> {
    const res = await api.get('/learning-analysis/export', {
      params: {
        kind: params.kind,
        course_id: params.courseId,
        student_id: params.studentId,
        format: params.format,
      },
      responseType: 'blob',
    })
    return res as unknown as Blob
  },
}
