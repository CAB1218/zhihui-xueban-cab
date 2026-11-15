/**
 * 智慧学伴 场景仪表盘类型定义
 * 所有场景仪表盘子组件共享的 TypeScript 接口
 */

// ============ 通用类型 ============

/** 课程状态枚举 */
export enum CourseStatus {
  ONGOING = 'ongoing',
  ENDED = 'ended',
  UPCOMING = 'upcoming',
}

/** 薄弱知识点严重程度 */
export enum WeaknessLevel {
  CRITICAL = 'critical',   // 红色
  WARNING = 'warning',     // 橙色
  CAUTION = 'caution',     // 黄色
}

/** 讨论类型 */
export enum DiscussionType {
  MY_QUESTION = 'my_question',
  PARTICIPATED = 'participated',
}

/** 快捷操作项 */
export interface QuickAction {
  label: string
  icon: string
  route: string
  buttonType: 'primary' | 'success' | 'warning' | 'danger' | 'info'
}

/** 统计项 */
export interface StatItem {
  label: string
  value: string | number
  icon: string
  color: string
}

// ============ 课堂模式 Mock 数据 ============

/** 课程表条目 */
export interface CourseScheduleItem {
  id: string
  name: string
  startTime: string         // '08:00'
  endTime: string           // '09:40'
  location: string
  status: CourseStatus
  teacher: string
}

/** 课后复习提醒 */
export interface ReviewReminderItem {
  courseId: string
  courseName: string
  description: string
  actionLabel: string
  actionRoute: string
}

// ============ 自习模式 Mock 数据 ============

/** 学习任务 */
export interface StudyTask {
  id: string
  title: string
  completed: boolean
  subject: string
  priority: 'high' | 'medium' | 'low'
}

/** 闪卡统计 */
export interface FlashcardStats {
  pendingReview: number
  masteryRate: number       // 0-100
  nextReviewTopic: string
}

/** 知识图谱迷你节点 */
export interface GraphNode {
  id: string
  label: string
  color: string
  isWeak: boolean
}

/** 知识图谱迷你数据 */
export interface KnowledgeGraphMini {
  totalNodes: number
  weakNodes: number
  nodes: GraphNode[]
}

/** 学习时长统计 */
export interface StudyTimeData {
  weekHours: string         // '12.5h'
  todayHours: string        // '2.3h'
  streakDays: number
}

// ============ 考前模式 Mock 数据 ============

/** 考试倒计时 */
export interface ExamCountdownData {
  daysLeft: number
  examName: string
  examDate: string          // ISO date string
}

/** 科目复习进度 */
export interface SubjectProgress {
  subject: string
  progress: number          // 0-100
}

/** 复习进度总览 */
export interface ReviewProgressData {
  overallProgress: number   // 0-100
  subjects: SubjectProgress[]
}

/** 错题本统计 */
export interface WrongBookStats {
  pendingReview: number
  mastered: number
  correctRate: number       // 0-100
}

/** 薄弱知识点 */
export interface WeakPoint {
  id: string
  name: string
  level: WeaknessLevel
}

// ============ 讨论模式 Mock 数据 ============

/** 热门话题 */
export interface DiscussionTopic {
  id: string
  title: string
  participants: number
  replies: number
  heatScore: number
  tags: string[]
}

/** 我的讨论条目 */
export interface MyDiscussionItem {
  id: string
  title: string
  type: DiscussionType
  newReplies: number
  resolved: boolean
}

// ============ 场景 Mock 数据聚合类型 ============

/** 课堂模式 mock 数据集合 */
export interface ClassroomMockData {
  stats: StatItem[]
  todayCourses: CourseScheduleItem[]
  reviewReminders: ReviewReminderItem[]
  toolbarActions: QuickAction[]
}

/** 自习模式 mock 数据集合 */
export interface SelfStudyMockData {
  stats: StatItem[]
  tasks: StudyTask[]
  flashcardStats: FlashcardStats
  graphMini: KnowledgeGraphMini
  studyTime: StudyTimeData
}

/** 考前模式 mock 数据集合 */
export interface ExamMockData {
  stats: StatItem[]
  countdown: ExamCountdownData
  reviewProgress: ReviewProgressData
  wrongBookStats: WrongBookStats
  weakPoints: WeakPoint[]
  toolbarActions: QuickAction[]
}

/** 讨论模式 mock 数据集合 */
export interface DiscussionMockData {
  stats: StatItem[]
  hotTopics: DiscussionTopic[]
  myDiscussions: MyDiscussionItem[]
  collabActions: QuickAction[]
}
