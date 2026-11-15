# PRD：学生成长档案（Student Growth Profile）

> **项目**: 智慧学伴 - AI 驱动的智慧教学平台
> **模块**: 学生成长档案
> **文档版本**: v1.0
> **创建日期**: 2025-07-09
> **产品经理**: 许清楚（Xu）
> **状态**: 待评审

---

## 1. 产品目标

### 1.1 核心问题

当前平台已积累大量学生学习行为数据（AI 对话、资源浏览、学习诊断、课程进度、笔记、复习卡片等），但这些数据分散在各功能模块中，**教师无法直观了解学生的整体学习轨迹，学生也缺乏自我回顾的统一入口**。

### 1.2 价值主张

学生成长档案模块通过 **自动聚合 + 人工评价** 的方式，将分散的学习行为数据整合为一份完整的、按时间线组织的成长档案，实现：

- **教师**：降低了解学生学情的成本，提供有据可依的评价与建议
- **学生**：获得学习历程的可视化回顾，激发学习动力与自我反思
- **管理者**：掌握全校/班级学生成长概况，辅助教学决策

---

## 2. 用户角色

| 角色 | 核心诉求 | 本模块能力 |
|------|---------|-----------|
| **教师** | 了解学生学习表现，给予针对性指导 | 查看学生成长档案、撰写评价与学习建议、查看班级对比 |
| **学生** | 了解自己的学习历程与不足 | 查看自己的成长档案、接收教师评价与建议 |
| **管理员** | 掌握整体学情概况 | 查看全校/全班级学生成长概况统计 |

---

## 3. 用户故事

### 3.1 教师用户故事

| 编号 | 用户故事 |
|------|---------|
| T-01 | 作为一名教师，我想查看某个学生的成长档案，以便全面了解该学生的学习轨迹和当前状态 |
| T-02 | 作为一名教师，我想给学生写文字评价和学习建议，以便针对性地指导学生改进学习方法 |
| T-03 | 作为一名教师，我想查看我所有学生的成长档案列表，以便快速浏览班级整体情况 |
| T-04 | 作为一名教师，我想查看班级学生成长对比数据，以便发现需要重点关注的学生 |
| T-05 | 作为一名教师，我想查看我过往给某个学生写的评价历史，以便跟踪建议的落实情况 |
| T-06 | 作为一名教师，我想导出学生成长档案为 PDF，以便在家长会或教研活动中使用 |

### 3.2 学生用户故事

| 编号 | 用户故事 |
|------|---------|
| S-01 | 作为一名学生，我想查看自己的成长档案，以便回顾自己的学习历程和进步情况 |
| S-02 | 作为一名学生，我想看到自己的学习行为时间线，以便了解自己在平台上做了什么 |
| S-03 | 作为一名学生，我想查看教师给我的评价和学习建议，以便改进自己的学习方法 |
| S-04 | 作为一名学生，我想看到自己的学习统计数据可视化，以便直观了解自己的学习投入 |
| S-05 | 作为一名学生，我想看到自己的诊断成绩变化趋势，以便了解薄弱环节是否改善 |

### 3.3 管理员用户故事

| 编号 | 用户故事 |
|------|---------|
| A-01 | 作为一名管理员，我想查看全校学生的成长概况统计，以便掌握整体教学效果 |
| A-02 | 作为一名管理员，我想按年级/班级筛选查看成长数据，以便进行分层教学分析 |

---

## 4. 需求池（P0 / P1 / P2）

### P0 — 必须实现

| 编号 | 需求 | 优先级 | 涉及角色 |
|------|------|--------|---------|
| P0-1 | 教师给学生写评价和学习建议 | P0 | 教师 |
| P0-2 | 学生查看自己的成长档案 | P0 | 学生 |
| P0-3 | 自动聚合学习行为数据，形成成长时间线 | P0 | 学生 / 教师 |
| P0-4 | 成长档案概览仪表盘（统计数据 + 可视化） | P0 | 学生 / 教师 |

### P1 — 应该实现

| 编号 | 需求 | 优先级 | 涉及角色 |
|------|------|--------|---------|
| P1-1 | 教师查看班级学生成长对比 | P1 | 教师 |
| P1-2 | 成长趋势图表（成绩变化、活跃度变化等） | P1 | 学生 / 教师 |
| P1-3 | 教师评价历史记录 | P1 | 教师 / 学生 |
| P1-4 | 成长档案导出（PDF） | P1 | 教师 / 学生 |

### P2 — 可以后续实现

| 编号 | 需求 | 优先级 | 涉及角色 |
|------|------|--------|---------|
| P2-1 | AI 自动生成成长分析报告 | P2 | 学生 / 教师 |
| P2-2 | 家长端查看（权限扩展） | P2 | 家长 |
| P2-3 | 成长档案分享 | P2 | 学生 |
| P2-4 | 同伴互评 | P2 | 学生 |

### 集思广益补充

| 编号 | 需求 | 优先级 | 涉及角色 | 说明 |
|------|------|--------|---------|------|
| E-1 | 成长里程碑标记 | P1 | 学生 / 教师 | 里程碑事件（首次完成诊断、连续学习7天、笔记达到100篇等）自动标记在时间线上 |
| E-2 | 教师评价提醒通知 | P1 | 学生 | 学生收到教师评价时，通过站内通知提醒 |
| E-3 | 学习习惯标签 | P2 | 学生 / 教师 | 基于行为数据自动生成标签（如"勤奋学习者"、"善于总结"、"主动提问"） |
| E-4 | 成长档案隐私控制 | P1 | 学生 | 学生可控制档案中部分内容的可见范围（如笔记是否对教师可见） |
| E-5 | 教师评价模板 | P2 | 教师 | 预设常用评价模板，教师可快速选择并微调，降低撰写成本 |
| E-6 | 班级成长看板 | P2 | 教师 / 管理员 | 班级维度的成长数据聚合看板，支持横向对比 |

---

## 5. 功能模块设计（P0）

### 5.1 教师评价与学习建议（P0-1）

**功能描述**：教师在查看学生成长档案时，可撰写文字评价和学习建议。

**交互流程**：
1. 教师进入学生成长档案页面
2. 在"教师评价"区域点击"写评价"按钮
3. 填写评价内容（富文本）和学习建议（富文本）
4. 可选择评价类型：阶段性评价 / 日常评价 / 专项建议
5. 提交后学生端收到通知

**数据模型**（新增）：

```
StudentEvaluation（学生评价表）
- id: int, PK
- tenant_id: int, FK
- student_id: int, FK → users.id
- teacher_id: int, FK → users.id
- course_id: int, FK → courses.id (可选，评价可关联具体课程)
- evaluation_type: str  # periodic / daily / targeted
- rating: int  # 综合评分 1-5
- content: text  # 评价内容
- suggestion: text  # 学习建议
- is_visible: bool  # 是否对学生可见，默认 true
- created_at: datetime
- updated_at: datetime
```

**API 设计**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/students/{id}/evaluations` | POST | 教师创建评价 |
| `/students/{id}/evaluations` | GET | 获取学生的评价列表 |
| `/evaluations/{id}` | PUT | 修改评价 |
| `/evaluations/{id}` | DELETE | 删除评价 |

**权限**：仅 teacher/admin/super_admin 可创建；学生仅可查看 is_visible=true 的评价。

---

### 5.2 学生成长档案查看（P0-2）

**功能描述**：学生查看自己的成长档案，包含个人信息、学习统计、成长时间线、教师评价。

**页面结构**：

```
学生成长档案页
├── 顶部信息卡：头像、昵称、年级、学校、注册时间、学习天数
├── 概览仪表盘（P0-4）
├── 成长时间线（P0-3）
├── 教师评价区域
└── 成长趋势图表（P1-2，后续迭代）
```

**前端路由**：
- 学生端：`/scene/:sceneType/growth-profile`（复用场景路由体系）
- 教师端查看学生档案：`/teacher/students/:studentId/growth-profile`

**前端视图目录**：新增 `frontend/src/views/growth/`
- `GrowthProfileView.vue` — 成长档案主页面
- `components/GrowthTimeline.vue` — 时间线组件
- `components/GrowthDashboard.vue` — 概览仪表盘组件
- `components/TeacherEvaluation.vue` — 教师评价组件

---

### 5.3 自动聚合成长时间线（P0-3）

**功能描述**：平台自动从各数据源聚合学生的学习行为事件，按时间倒序形成成长时间线。

**时间线事件类型**：

| 事件类型 | 图标 | 数据来源 | 展示内容 |
|---------|------|---------|---------|
| AI 对话 | 💬 | `AgentSession` + `AgentMessage` | 会话标题、消息数、智能体类型、时间 |
| 学习诊断 | 📝 | `Diagnosis` | 诊断标题、得分、强项/弱点、时间 |
| 资源浏览/下载 | 📎 | `AnalyticsEvent`(resource_download) + `ResourceFavorite` | 资源标题、类型、时间 |
| 笔记创建/更新 | ✏️ | `Note` | 笔记标题、字数、时间 |
| 复习卡片 | 🔖 | `FlashCard` | 卡片知识点、复习次数、时间 |
| 课程进度 | 📊 | `CourseEnrollment` | 课程名称、进度变化、时间 |
| 课堂参与 | 🙋 | `ClassroomParticipant` + `ClassroomPollVote` | 课堂主题、参与行为（举手/投票）、时间 |
| 知识图谱浏览 | 🗺️ | `AnalyticsEvent`(graph_browse / node_click) | 浏览的知识点、时间 |

**后端聚合逻辑**：

```python
# backend/app/api/v1/growth.py（新增）
@router.get("/students/{student_id}/timeline")
async def get_growth_timeline(
    student_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    event_types: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
):
    """
    聚合查询学生成长时间线：
    1. 并行查询各数据源（AgentSession, Diagnosis, Note, FlashCard, ...）
    2. 统一转换为 TimelineEvent 格式 {type, title, description, timestamp, metadata}
    3. 按时间倒序合并、分页返回
    4. 支持按事件类型和时间范围筛选
    """
```

**设计要点**：
- 时间线默认展示最近 30 天事件，支持时间范围筛选
- 支持按事件类型筛选（如只看诊断、只看 AI 对话）
- 分页加载，每页 50 条
- 聚合查询通过 `asyncio.gather` 并行执行，降低延迟

---

### 5.4 成长档案概览仪表盘（P0-4）

**功能描述**：以数据卡片 + 图表的形式展示学生关键学习统计数据。

**仪表盘卡片**：

| 卡片 | 数据来源 | 展示内容 |
|------|---------|---------|
| 学习天数 | `User.created_at` + `AnalyticsEvent` | 注册至今天数、活跃学习天数 |
| AI 对话次数 | `AgentSession` | 总会话数、总消息数 |
| 诊断次数与平均分 | `Diagnosis` | 诊断总次数、平均得分、最近得分 |
| 课程进度 | `CourseEnrollment` | 已选课程数、平均完成进度 |
| 笔记数量 | `Note` | 笔记总数、总字数 |
| 复习卡片 | `FlashCard` | 卡片总数、待复习数、已掌握数 |
| 资源互动 | `ResourceFavorite` + `AnalyticsEvent` | 收藏数、浏览数、下载数 |
| 课堂参与 | `ClassroomParticipant` | 参与课堂数、举手次数、投票次数 |

**可视化图表**（使用 ECharts）：

| 图表 | 类型 | 数据来源 | 说明 |
|------|------|---------|------|
| 学习活跃度热力图 | 日历热力图 | `AnalyticsEvent` | 按日统计事件数量，类似 GitHub 贡献图 |
| 诊断成绩趋势 | 折线图 | `Diagnosis` | X 轴时间，Y 轴得分 |
| 学习行为分布 | 饼图 | 聚合数据 | 各类学习行为占比 |
| 课程进度概览 | 进度条列表 | `CourseEnrollment` | 各课程完成进度 |

**API 设计**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/students/{id}/growth/overview` | GET | 获取成长概览统计数据 |
| `/students/{id}/growth/timeline` | GET | 获取成长时间线（分页） |
| `/students/{id}/growth/trends` | GET | 获取趋势图表数据（P1） |

**复用已有 API**：`GET /dashboard/stats` 的统计逻辑可复用并扩展。

---

## 6. 数据来源映射

### 6.1 现有数据源映射

| 成长档案数据类别 | 数据模型 | 表名 | 文件路径 | 关键字段 |
|----------------|---------|------|---------|---------|
| 学生基本信息 | `User` | `users` | `backend/app/models/user.py` | nickname, grade, school, bio, created_at |
| AI 学习对话 | `AgentSession` | `agent_sessions` | `backend/app/models/agent.py` | user_id, agent_type, title, message_count, last_message_at, created_at |
| AI 对话消息 | `AgentMessage` | `agent_messages` | `backend/app/models/agent.py` | session_id, role, content, content_type, created_at |
| 学习诊断记录 | `Diagnosis` | `diagnoses` | `backend/app/models/diagnosis.py` | user_id, title, score, weaknesses, strengths, recommendations, completed_at |
| 诊断题目详情 | `DiagnosisQuestion` | `diagnosis_questions` | `backend/app/models/diagnosis.py` | diagnosis_id, question_type, is_correct, knowledge_points, difficulty |
| 课程信息 | `Course` | `courses` | `backend/app/models/course.py` | name, subject, grade, teacher_id |
| 课程学习进度 | `CourseEnrollment` | `course_enrollments` | `backend/app/models/course.py` | course_id, user_id, progress, enrolled_at |
| 学习资源 | `Resource` | `resources` | `backend/app/models/resource.py` | title, resource_type, view_count, download_count |
| 资源收藏 | `ResourceFavorite` | `resource_favorites` | `backend/app/models/resource.py` | user_id, resource_id, created_at |
| 学习笔记 | `Note` | `notes` | `backend/app/models/note.py` | title, owner_id, note_type, word_count, course_id, created_at |
| 笔记版本 | `NoteVersion` | `note_versions` | `backend/app/models/note.py` | note_id, version, change_summary, created_at |
| 复习卡片 | `FlashCard` | `flash_cards` | `backend/app/models/flash_card.py` | user_id, knowledge_point, repetition_count, ease_factor, next_review_at |
| 课堂参与 | `ClassroomParticipant` | `classroom_participants` | `backend/app/models/classroom.py` | classroom_id, user_id, hand_raised, joined_at |
| 课堂投票 | `ClassroomPollVote` | `classroom_poll_votes` | `backend/app/models/classroom.py` | poll_id, user_id, created_at |
| 行为分析事件 | `AnalyticsEvent` | `analytics_events` | `backend/app/models/analytics.py` | user_id, event_type, event_data, timestamp |
| 学伴互动 | `Buddy` | `buddies` | `backend/app/models/buddy.py` | user_id, level, experience_points, mood_score |

### 6.2 AnalyticsEvent 事件类型映射

| 事件类型 | 枚举值 | 成长档案用途 |
|---------|--------|-------------|
| 页面浏览 | `page_view` | 学习活跃度统计 |
| 资源上传 | `resource_upload` | 教师上传资源行为（不用于学生档案） |
| 资源下载 | `resource_download` | 资源互动时间线事件 |
| 搜索查询 | `search_query` | 学习主动性分析 |
| 图谱浏览 | `graph_browse` | 知识探索时间线事件 |
| 知识点点击 | `node_click` | 知识探索时间线事件 |
| AI 对话 | `ai_chat` | AI 对话活跃度统计 |
| 场景切换 | `scene_switch` | 学习场景偏好分析 |

### 6.3 新增数据模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `StudentEvaluation` | `student_evaluations` | 教师对学生的评价与学习建议 |

### 6.4 已有 API 复用

| API 端点 | 复用方式 |
|---------|---------|
| `GET /dashboard/stats` | 统计逻辑参考，成长概览 API 在此基础上扩展 |
| `GET /teachers/students` | 教师查看学生列表，成长档案入口 |
| `GET /teachers/analytics` | 学情分析数据，可对比参考 |
| `GET /diagnosis/history` | 诊断历史，成长时间线数据来源之一 |

---

## 7. 技术方案概述

### 7.1 后端

| 方面 | 方案 |
|------|------|
| 新增文件 | `backend/app/models/evaluation.py`、`backend/app/api/v1/growth.py`、`backend/app/schemas/growth.py`、`backend/app/services/growth_service.py` |
| 聚合查询 | `growth_service.py` 封装时间线聚合逻辑，`asyncio.gather` 并行查询各数据源 |
| ClickHouse 查询 | `AnalyticsEvent` 查询走 ClickHouse，与 PostgreSQL 查询并行执行 |
| 缓存 | 概览统计数据使用 Redis 缓存，TTL 5 分钟（key: `growth:overview:{student_id}`） |
| 权限 | 学生只能查看自己的档案；教师只能查看自己课程下的学生档案；管理员可查看全部 |

### 7.2 前端

| 方面 | 方案 |
|------|------|
| 新增目录 | `frontend/src/views/growth/` |
| 路由 | 学生端 `scene-routes.ts` 新增 `/scene/:sceneType/growth-profile`；教师端 `teacher-routes.ts` 新增 `/teacher/students/:studentId/growth-profile` |
| 状态管理 | 新增 `frontend/src/stores/growth.ts`（Pinia） |
| 图表库 | ECharts（Vue3 封装 `vue-echarts`） |
| 时间线组件 | 基于 Element Plus `el-timeline` 封装 |

---

## 8. 待确认问题

| 编号 | 问题 | 影响范围 | 建议方案 |
|------|------|---------|---------|
| Q-1 | 教师评价是否需要关联具体课程？还是可以对学生的整体表现评价？ | 数据模型、评价表单设计 | 建议两者都支持：course_id 可选，无 course_id 时为整体评价 |
| Q-2 | 学生是否可以回复教师的评价？ | 交互设计、数据模型 | 建议 P0 仅支持单向评价，P2 增加学生回复功能 |
| Q-3 | 成长时间线是否展示 AI 对话的具体内容？还是仅展示会话标题？ | 隐私、性能 | 建议仅展示会话标题和摘要，点击可跳转到原会话 |
| Q-4 | 教师是否只能查看自己课程下的学生档案？还是可以查看所有学生？ | 权限设计 | 建议教师仅能查看自己课程下的学生，管理员可查看全部 |
| Q-5 | 成长档案概览数据的更新频率？实时还是定时刷新？ | 性能、缓存策略 | 建议概览数据 Redis 缓存 5 分钟，时间线实时查询 |
| Q-6 | 是否需要支持家长端查看？如果需要，家长账号体系如何设计？ | P2 功能规划 | 建议 P2 阶段设计家长账号体系，通过邀请码关联学生 |
| Q-7 | 评价内容是否支持富文本（图片、链接等）？ | 表单组件选择 | 建议支持基础富文本（加粗、列表、链接），不支持图片上传 |
| Q-8 | 班级学生成长对比（P1）的对比维度有哪些？ | P1 功能设计 | 建议对比维度：诊断平均分、学习活跃度、课程完成进度、笔记数量 |
| Q-9 | 成长里程碑（E-1）的触发规则是否可配置？ | E-1 功能设计 | 建议预设规则，P2 阶段开放自定义 |
| Q-10 | 时间线事件量很大时（如活跃学生半年上千条），是否需要智能摘要？ | 性能、体验 | 建议支持按天/周聚合展示，P2 阶段引入 AI 生成摘要 |

---

## 9. 里程碑规划

| 阶段 | 内容 | 涉及需求 |
|------|------|---------|
| **阶段一** | P0 核心功能开发 | P0-1 ~ P0-4 |
| **阶段二** | P1 增强功能 | P1-1 ~ P1-4、E-1、E-2、E-4 |
| **阶段三** | P2 扩展功能 | P2-1 ~ P2-4、E-3、E-5、E-6 |

---

> **文档作者**: 许清楚（Xu）· 产品经理
> **审核人**: 陈安国（项目负责人）
> **下次更新**: 评审后根据反馈修订
