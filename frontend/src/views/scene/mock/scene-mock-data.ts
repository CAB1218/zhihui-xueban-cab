/**
 * 智慧学伴 场景仪表盘集中 Mock 数据
 * 按场景分组导出，P2 阶段替换为 API 调用时只需改数据源
 */
import {
  CourseStatus,
  WeaknessLevel,
  DiscussionType,
} from '../types'
import type {
  StatItem,
  CourseScheduleItem,
  ReviewReminderItem,
  QuickAction,
  StudyTask,
  FlashcardStats,
  KnowledgeGraphMini,
  StudyTimeData,
  ExamCountdownData,
  ReviewProgressData,
  WrongBookStats,
  WeakPoint,
  DiscussionTopic,
  MyDiscussionItem,
  ClassroomMockData,
  SelfStudyMockData,
  ExamMockData,
  DiscussionMockData,
} from '../types'

// ============ 课堂模式 Mock 数据 ============

/** 课堂模式统计卡 */
const classroomStats: StatItem[] = [
  { label: '今日课程', value: 4, icon: 'Calendar', color: '#1976D2' },
  { label: '已完成', value: 1, icon: 'CircleCheck', color: '#388E3C' },
  { label: '笔记数', value: 28, icon: 'EditPen', color: '#F57C00' },
  { label: '本周学习', value: '12.5h', icon: 'Timer', color: '#7B1FA2' },
]

/** 课堂模式今日课程（status 字段为初始值，运行时由 dayjs 重新计算） */
const classroomTodayCourses: CourseScheduleItem[] = [
  {
    id: 'course-001',
    name: '高等数学',
    startTime: '08:00',
    endTime: '09:40',
    location: '教学楼A301',
    status: CourseStatus.ENDED,
    teacher: '王教授',
  },
  {
    id: 'course-002',
    name: '大学物理',
    startTime: '10:00',
    endTime: '11:40',
    location: '教学楼B205',
    status: CourseStatus.ONGOING,
    teacher: '李教授',
  },
  {
    id: 'course-003',
    name: '数据结构',
    startTime: '14:00',
    endTime: '15:40',
    location: '实验楼401',
    status: CourseStatus.UPCOMING,
    teacher: '张教授',
  },
  {
    id: 'course-004',
    name: '英语口语',
    startTime: '16:00',
    endTime: '17:30',
    location: '外语楼102',
    status: CourseStatus.UPCOMING,
    teacher: 'Smith 老师',
  },
]

/** 课堂模式课后复习提醒 */
const classroomReviewReminders: ReviewReminderItem[] = [
  {
    courseId: 'course-001',
    courseName: '高等数学',
    description: '回顾今日笔记，AI 自动生成复习要点',
    actionLabel: '开始复习',
    actionRoute: 'notes',
  },
  {
    courseId: 'course-002',
    courseName: '大学物理',
    description: '课后 15 分钟回顾牛顿运动定律',
    actionLabel: '稍后提醒',
    actionRoute: 'notes',
  },
]

/** 课堂模式工具栏操作（route 为场景子路径，由 navigateToSceneRoute 拼接） */
const classroomToolbarActions: QuickAction[] = [
  { label: '随堂测验', icon: 'Document', route: 'diagnosis', buttonType: 'warning' },
  { label: '举手提问', icon: 'ChatLineSquare', route: 'agent', buttonType: 'primary' },
  { label: '查看板书', icon: 'Notebook', route: 'notes', buttonType: 'success' },
  { label: '课程资源', icon: 'Folder', route: 'resources', buttonType: 'info' },
]

/** 课堂模式 Mock 数据聚合 */
export const classroomMockData: ClassroomMockData = {
  stats: classroomStats,
  todayCourses: classroomTodayCourses,
  reviewReminders: classroomReviewReminders,
  toolbarActions: classroomToolbarActions,
}

// ============ 自习模式 Mock 数据 ============

/** 自习模式统计卡 */
const selfStudyStats: StatItem[] = [
  { label: '今日任务', value: '1/3', icon: 'List', color: '#388E3C' },
  { label: '待复习闪卡', value: 15, icon: 'Postcard', color: '#1976D2' },
  { label: '知识点数', value: 128, icon: 'Connection', color: '#F57C00' },
  { label: '连续打卡', value: '7天', icon: 'Medal', color: '#D32F2F' },
]

/** 自习模式学习任务 */
const selfStudyTasks: StudyTask[] = [
  {
    id: 'task-001',
    title: '复习数据结构第三章',
    completed: true,
    subject: '数据结构',
    priority: 'high',
  },
  {
    id: 'task-002',
    title: '完成 20 道高数练习题',
    completed: false,
    subject: '高等数学',
    priority: 'high',
  },
  {
    id: 'task-003',
    title: '整理物理实验报告',
    completed: false,
    subject: '大学物理',
    priority: 'medium',
  },
]

/** 自习模式闪卡统计 */
const selfStudyFlashcardStats: FlashcardStats = {
  pendingReview: 15,
  masteryRate: 72,
  nextReviewTopic: '高数 · 极限',
}

/** 自习模式知识图谱迷你数据（7 节点，2 个薄弱节点标红） */
const selfStudyGraphMini: KnowledgeGraphMini = {
  totalNodes: 7,
  weakNodes: 2,
  nodes: [
    { id: 'n1', label: '微积分', color: '#42A5F5', isWeak: false },
    { id: 'n2', label: '导数', color: '#66BB6A', isWeak: false },
    { id: 'n3', label: '极限', color: '#EF5350', isWeak: true },
    { id: 'n4', label: '连续性', color: '#42A5F5', isWeak: false },
    { id: 'n5', label: '积分', color: '#66BB6A', isWeak: false },
    { id: 'n6', label: '级数', color: '#EF5350', isWeak: true },
    { id: 'n7', label: '微分方程', color: '#42A5F5', isWeak: false },
  ],
}

/** 自习模式学习时长统计 */
const selfStudyStudyTime: StudyTimeData = {
  weekHours: '12.5h',
  todayHours: '2.3h',
  streakDays: 7,
}

/** 自习模式 Mock 数据聚合 */
export const selfStudyMockData: SelfStudyMockData = {
  stats: selfStudyStats,
  tasks: selfStudyTasks,
  flashcardStats: selfStudyFlashcardStats,
  graphMini: selfStudyGraphMini,
  studyTime: selfStudyStudyTime,
}

// ============ 考前模式 Mock 数据 ============

/** 考前模式统计卡 */
const examStats: StatItem[] = [
  { label: '错题数', value: 24, icon: 'Warning', color: '#F57C00' },
  { label: '模拟考试', value: 3, icon: 'Document', color: '#1976D2' },
  { label: '复习进度', value: '68%', icon: 'TrendCharts', color: '#388E3C' },
  { label: '倒计时', value: '14天', icon: 'Timer', color: '#D32F2F' },
]

/** 考前模式倒计时（P0 固定 14 天） */
const examCountdown: ExamCountdownData = {
  daysLeft: 14,
  examName: '期末考试',
  examDate: '2025-07-24',
}

/** 考前模式复习进度 */
const examReviewProgress: ReviewProgressData = {
  overallProgress: 68,
  subjects: [
    { subject: '高等数学', progress: 80 },
    { subject: '大学物理', progress: 55 },
    { subject: '数据结构', progress: 72 },
    { subject: '线性代数', progress: 45 },
  ],
}

/** 考前模式错题本统计 */
const examWrongBookStats: WrongBookStats = {
  pendingReview: 24,
  mastered: 156,
  correctRate: 89,
}

/** 考前模式薄弱知识点 */
const examWeakPoints: WeakPoint[] = [
  { id: 'wp-001', name: '极限计算', level: WeaknessLevel.CRITICAL },
  { id: 'wp-002', name: '牛顿运动定律', level: WeaknessLevel.CRITICAL },
  { id: 'wp-003', name: '矩阵特征值', level: WeaknessLevel.WARNING },
  { id: 'wp-004', name: '二叉树遍历', level: WeaknessLevel.WARNING },
  { id: 'wp-005', name: '光的干涉', level: WeaknessLevel.CAUTION },
]

/** 考前模式工具栏操作 */
const examToolbarActions: QuickAction[] = [
  { label: '限时训练', icon: 'AlarmClock', route: 'diagnosis', buttonType: 'danger' },
  { label: '模拟考试', icon: 'Document', route: 'diagnosis', buttonType: 'warning' },
  { label: '错题重练', icon: 'EditPen', route: 'diagnosis', buttonType: 'primary' },
  { label: '知识点速查', icon: 'Search', route: 'graphs', buttonType: 'info' },
]

/** 考前模式 Mock 数据聚合 */
export const examMockData: ExamMockData = {
  stats: examStats,
  countdown: examCountdown,
  reviewProgress: examReviewProgress,
  wrongBookStats: examWrongBookStats,
  weakPoints: examWeakPoints,
  toolbarActions: examToolbarActions,
}

// ============ 讨论模式 Mock 数据 ============

/** 讨论模式统计卡 */
const discussionStats: StatItem[] = [
  { label: '讨论数', value: 8, icon: 'ChatDotRound', color: '#7B1FA2' },
  { label: '参与人数', value: 32, icon: 'User', color: '#1976D2' },
  { label: '白板数', value: 2, icon: 'Monitor', color: '#388E3C' },
  { label: '投票数', value: 5, icon: 'CheckBox', color: '#F57C00' },
]

/** 讨论模式热门话题 */
const discussionHotTopics: DiscussionTopic[] = [
  {
    id: 'topic-001',
    title: '递归算法的优化策略',
    participants: 12,
    replies: 28,
    heatScore: 95,
    tags: ['算法', '数据结构'],
  },
  {
    id: 'topic-002',
    title: '牛顿力学的适用范围',
    participants: 8,
    replies: 15,
    heatScore: 72,
    tags: ['物理'],
  },
  {
    id: 'topic-003',
    title: '数据库索引优化方案',
    participants: 6,
    replies: 11,
    heatScore: 58,
    tags: ['数据库', '后端'],
  },
  {
    id: 'topic-004',
    title: '线性代数特征值分解的几何意义',
    participants: 5,
    replies: 9,
    heatScore: 45,
    tags: ['数学', '线性代数'],
  },
]

/** 讨论模式我的讨论动态 */
const discussionMyDiscussions: MyDiscussionItem[] = [
  {
    id: 'disc-001',
    title: '极限计算的疑问：洛必达法则的适用条件',
    type: DiscussionType.MY_QUESTION,
    newReplies: 2,
    resolved: false,
  },
  {
    id: 'disc-002',
    title: '矩阵分解的问题：什么时候用 LU 分解？',
    type: DiscussionType.MY_QUESTION,
    newReplies: 0,
    resolved: true,
  },
  {
    id: 'disc-003',
    title: '递归优化策略的讨论',
    type: DiscussionType.PARTICIPATED,
    newReplies: 3,
    resolved: false,
  },
  {
    id: 'disc-004',
    title: '数据库索引选择的实践经验',
    type: DiscussionType.PARTICIPATED,
    newReplies: 0,
    resolved: true,
  },
  {
    id: 'disc-005',
    title: '物理实验数据处理方法交流',
    type: DiscussionType.PARTICIPATED,
    newReplies: 1,
    resolved: false,
  },
]

/** 讨论模式协作工具操作 */
const discussionCollabActions: QuickAction[] = [
  { label: '协作白板', icon: 'Edit', route: 'buddy', buttonType: 'primary' },
  { label: '共享笔记', icon: 'Notebook', route: 'notes', buttonType: 'success' },
  { label: '发起讨论', icon: 'ChatLineSquare', route: 'agent', buttonType: 'warning' },
  { label: '知识问答', icon: 'QuestionFilled', route: 'agent', buttonType: 'info' },
]

/** 讨论模式 Mock 数据聚合 */
export const discussionMockData: DiscussionMockData = {
  stats: discussionStats,
  hotTopics: discussionHotTopics,
  myDiscussions: discussionMyDiscussions,
  collabActions: discussionCollabActions,
}
