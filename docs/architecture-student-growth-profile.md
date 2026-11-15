# 学生成长档案模块 — 架构设计文档

> 架构师：高见远（Gao）
> 日期：2026-07-09
> 关联 PRD：`docs/prd-student-growth-profile.md`

---

## 1. 实现方案 + 框架选型

### 1.1 总体方案

学生成长档案模块分为 **三大功能域**：

| 功能域 | 实现策略 |
|--------|---------|
| **教师评价** | 新增 `StudentEvaluation` 模型，标准 CRUD API，教师写评价、学生查看 |
| **自动聚合时间线** | `GrowthService` 从 7 个 PostgreSQL 数据源 + 1 个 ClickHouse 数据源聚合查询，统一封装为 `TimelineItem` 列表返回 |
| **概览仪表盘** | `GrowthService` 聚合统计各维度数据（对话数、诊断数、笔记数、卡片数等），返回 `GrowthDashboard` 结构 |

### 1.2 技术选型

| 层 | 选型 | 说明 |
|----|------|------|
| 后端 ORM | SQLAlchemy 2.0 (Mapped 风格) | 与现有模型一致 |
| API | FastAPI + APIRouter | 与现有路由模式一致 |
| Schema | Pydantic v2 BaseModel | 与现有 schemas 一致 |
| 聚合查询 | SQLAlchemy async select | PostgreSQL 源；httpx HTTP 调用 ClickHouse |
| 迁移 | Alembic | 手动编写迁移脚本 |
| 前端 UI | Vue3 `<script setup>` + Element Plus | 与现有组件一致 |
| 前端状态 | Pinia Setup Store | 与现有 store 一致 |
| 前端图表 | ECharts 5.x | 仪表盘需要饼图/柱状图/折线图 |
| 前端 HTTP | 现有 `services/api.ts` axios 实例 | 复用拦截器 |

### 1.3 聚合策略

时间线聚合采用 **懒加载分页** 策略，而非全量合并：

1. 前端请求 `GET /growth/timeline?student_id=&page=1&page_size=20`
2. 后端 `GrowthService.get_timeline()` 并发查询各数据源最近记录（各取 `page_size` 条）
3. 合并后按 `timestamp` 倒序排序，截取对应分页区间
4. 返回 `PaginatedResponse[TimelineItem]`

> **注意**：此策略在数据量大时各源取 `page_size * 2` 条做归并排序，保证分页正确性，避免全量扫描。

---

## 2. 文件列表及相对路径

### 2.1 后端文件

| # | 路径 | 类型 | 说明 |
|---|------|------|------|
| B1 | `backend/app/models/evaluation.py` | [新建] | StudentEvaluation ORM 模型 |
| B2 | `backend/app/models/__init__.py` | [修改] | 注册 StudentEvaluation 导入 |
| B3 | `backend/app/schemas/growth.py` | [新建] | Pydantic schemas（请求/响应） |
| B4 | `backend/app/services/growth_service.py` | [新建] | 聚合查询服务 |
| B5 | `backend/app/api/v1/growth.py` | [新建] | 成长档案 API 路由 |
| B6 | `backend/app/api/v1/router.py` | [修改] | 注册 growth 路由 |
| B7 | `backend/migrations/versions/d4f5a6b7c802_add_student_evaluations.py` | [新建] | Alembic 迁移 |

### 2.2 前端文件

| # | 路径 | 类型 | 说明 |
|---|------|------|------|
| F1 | `frontend/src/services/growth.ts` | [新建] | API 服务 + TypeScript 类型定义 |
| F2 | `frontend/src/stores/growth.ts` | [新建] | Pinia store |
| F3 | `frontend/src/views/growth/GrowthProfileView.vue` | [新建] | 成长档案主页面 |
| F4 | `frontend/src/views/growth/components/GrowthTimeline.vue` | [新建] | 时间线组件 |
| F5 | `frontend/src/views/growth/components/GrowthDashboard.vue` | [新建] | 概览仪表盘组件 |
| F6 | `frontend/src/views/growth/components/TeacherEvaluationCard.vue` | [新建] | 教师评价卡片组件 |
| F7 | `frontend/src/views/growth/components/EvaluationForm.vue` | [新建] | 评价表单组件（教师用） |
| F8 | `frontend/src/router/routes/scene-routes.ts` | [修改] | 添加学生端路由 |
| F9 | `frontend/src/router/routes/teacher-routes.ts` | [修改] | 添加教师端路由 |
| F10 | `frontend/src/components/layout/Sidebar.vue` | [修改] | featureMenus 添加"成长档案"菜单项 |

**合计**：新建 12 个文件，修改 5 个文件。

---

## 3. 数据结构和接口设计

### 3.1 StudentEvaluation 模型（SQLAlchemy）

> 文件：`backend/app/models/evaluation.py`

```python
"""
智慧学伴 学生评价 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudentEvaluation(Base):
    """学生评价表 — 教师对学生的成长评价"""

    __tablename__ = "student_evaluations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="评价ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="学生用户ID"
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="教师用户ID"
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("courses.id"), nullable=True, index=True, comment="关联课程ID(可选)"
    )
    evaluation_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="评价类型: overall/academic/attitude/improvement"
    )
    rating: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="评分1-5星"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="评价内容"
    )
    suggestion: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="学习建议"
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否对学生可见"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间"
    )
```

**字段说明**：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK, autoincrement | 评价ID |
| `tenant_id` | Integer | FK→tenants.id, NOT NULL, indexed | 租户ID |
| `student_id` | Integer | FK→users.id, NOT NULL, indexed | 被评价学生ID |
| `teacher_id` | Integer | FK→users.id, NOT NULL, indexed | 评价教师ID |
| `course_id` | Integer | FK→courses.id, nullable, indexed | 关联课程（可选） |
| `evaluation_type` | String(30) | NOT NULL | 评价类型：`overall`(综合) / `academic`(学业) / `attitude`(态度) / `improvement`(进步) |
| `rating` | Integer | NOT NULL | 评分 1-5 |
| `content` | Text | NOT NULL | 评价正文 |
| `suggestion` | Text | nullable | 学习建议 |
| `is_visible` | Boolean | default=True | 是否对学生可见（教师可设为不可见，暂存草稿） |
| `created_at` | DateTime | NOT NULL | 创建时间 |
| `updated_at` | DateTime | NOT NULL | 更新时间 |

**索引**：
- `ix_student_evaluations_tenant_id` — 租户隔离查询
- `ix_student_evaluations_student_id` — 按学生查询（最高频）
- `ix_student_evaluations_teacher_id` — 教师查看自己写的评价
- `ix_student_evaluations_course_id` — 按课程筛选

### 3.2 Pydantic Schemas

> 文件：`backend/app/schemas/growth.py`

```python
"""
智慧学伴 成长档案 Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 评价相关 ====================

class EvaluationCreate(BaseModel):
    """创建评价请求"""
    student_id: int = Field(..., description="学生用户ID")
    course_id: Optional[int] = Field(None, description="关联课程ID(可选)")
    evaluation_type: str = Field(
        "overall",
        description="评价类型: overall/academic/attitude/improvement",
    )
    rating: int = Field(..., ge=1, le=5, description="评分1-5")
    content: str = Field(..., min_length=1, max_length=5000, description="评价内容")
    suggestion: Optional[str] = Field(None, max_length=3000, description="学习建议")
    is_visible: bool = Field(True, description="是否对学生可见")


class EvaluationUpdate(BaseModel):
    """更新评价请求"""
    evaluation_type: Optional[str] = Field(None, description="评价类型")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分")
    content: Optional[str] = Field(None, min_length=1, max_length=5000, description="评价内容")
    suggestion: Optional[str] = Field(None, max_length=3000, description="学习建议")
    is_visible: Optional[bool] = Field(None, description="是否可见")


class EvaluationResponse(BaseModel):
    """评价响应"""
    id: int
    student_id: int
    teacher_id: int
    teacher_name: str = Field("", description="教师姓名(联表查询)")
    course_id: Optional[int] = None
    course_name: Optional[str] = Field(None, description="课程名称(联表查询)")
    evaluation_type: str
    rating: int
    content: str
    suggestion: Optional[str] = None
    is_visible: bool
    created_at: datetime
    updated_at: datetime


# ==================== 时间线相关 ====================

class TimelineItem(BaseModel):
    """时间线条目 — 统一封装各数据源的事件"""
    source: str = Field(..., description="数据来源: evaluation/agent/diagnosis/note/flashcard/course/resource/classroom")
    event_type: str = Field(..., description="事件类型: 如 ai_chat/diagnosis_completed/note_created 等")
    title: str = Field(..., description="事件标题")
    description: Optional[str] = Field(None, description="事件描述/摘要")
    timestamp: datetime = Field(..., description="事件时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据(如 score/course_name 等)")


# ==================== 仪表盘相关 ====================

class DashboardStatCard(BaseModel):
    """仪表盘统计卡片"""
    key: str = Field(..., description="统计键: ai_chat_count/diagnosis_count/note_count 等")
    label: str = Field(..., description="显示标签: AI对话数/诊断次数 等")
    value: int = Field(0, description="数值")
    icon: Optional[str] = Field(None, description="图标名称")


class GrowthDashboard(BaseModel):
    """成长仪表盘数据"""
    stat_cards: List[DashboardStatCard] = Field(default_factory=list, description="统计卡片列表")
    weekly_activity: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="近7天活动趋势 [{date: '2026-07-01', count: 12}, ...]",
    )
    subject_distribution: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="学科分布 [{subject: 'math', count: 5}, ...]",
    )
    recent_evaluations: List[EvaluationResponse] = Field(
        default_factory=list, description="最近教师评价(最多3条)"
    )
```

### 3.3 API 端点定义

> 文件：`backend/app/api/v1/growth.py`
> 前缀：`/api/v1/growth`（在 router.py 中注册）

| # | 方法 | 路径 | 请求体 | 响应体 | 权限 | 说明 |
|---|------|------|--------|--------|------|------|
| 1 | POST | `/evaluations` | `EvaluationCreate` | `APIResponse[EvaluationResponse]` | teacher, admin | 教师创建评价 |
| 2 | GET | `/evaluations` | Query: `student_id`, `course_id?`, `page`, `page_size` | `APIResponse[PaginatedResponse[EvaluationResponse]]` | teacher, admin | 教师查看学生评价列表 |
| 3 | GET | `/evaluations/{evaluation_id}` | — | `APIResponse[EvaluationResponse]` | teacher, admin | 获取评价详情 |
| 4 | PUT | `/evaluations/{evaluation_id}` | `EvaluationUpdate` | `APIResponse[EvaluationResponse]` | teacher, admin (仅作者) | 更新评价 |
| 5 | DELETE | `/evaluations/{evaluation_id}` | — | `APIResponse[None]` | teacher, admin (仅作者) | 删除评价 |
| 6 | GET | `/timeline` | Query: `student_id`, `source?`, `page`, `page_size` | `APIResponse[PaginatedResponse[TimelineItem]]` | student(仅自己) / teacher / admin | 获取成长时间线 |
| 7 | GET | `/dashboard` | Query: `student_id?` | `APIResponse[GrowthDashboard]` | student(仅自己) / teacher / admin | 获取仪表盘数据 |

**权限规则**：
- 学生只能查看自己的档案：`student_id` 必须等于 `current_user.id`，否则 403
- 教师/管理员可查看任意学生档案
- 评价的创建/修改/删除仅限 teacher/admin，且修改/删除仅限评价作者

**API 详细定义**：

```python
# ========== 评价管理 ==========

@router.post("/evaluations", summary="创建学生评价")
async def create_evaluation(
    body: EvaluationCreate,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[EvaluationResponse]:
    ...

@router.get("/evaluations", summary="获取学生评价列表")
async def list_evaluations(
    student_id: int = Query(..., description="学生ID"),
    course_id: Optional[int] = Query(None, description="课程ID筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[PaginatedResponse[EvaluationResponse]]:
    ...

@router.get("/evaluations/{evaluation_id}", summary="获取评价详情")
async def get_evaluation(
    evaluation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[EvaluationResponse]:
    ...

@router.put("/evaluations/{evaluation_id}", summary="更新评价")
async def update_evaluation(
    evaluation_id: int,
    body: EvaluationUpdate,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[EvaluationResponse]:
    ...

@router.delete("/evaluations/{evaluation_id}", summary="删除评价")
async def delete_evaluation(
    evaluation_id: int,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    ...

# ========== 时间线 ==========

@router.get("/timeline", summary="获取成长时间线")
async def get_timeline(
    student_id: int = Query(..., description="学生ID"),
    source: Optional[str] = Query(None, description="数据源筛选: evaluation/agent/diagnosis/note/flashcard/course/resource/classroom"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[PaginatedResponse[TimelineItem]]:
    ...

# ========== 仪表盘 ==========

@router.get("/dashboard", summary="获取成长仪表盘")
async def get_dashboard(
    student_id: Optional[int] = Query(None, description="学生ID(教师端传, 学生端不传则用自己)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[GrowthDashboard]:
    ...
```

### 3.4 GrowthService 核心方法签名

> 文件：`backend/app/services/growth_service.py`

```python
"""
智慧学伴 成长档案聚合服务
从多个数据源聚合学生学习行为数据
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentSession
from app.models.classroom import ClassroomParticipant, ClassroomPollVote
from app.models.course import CourseEnrollment
from app.models.diagnosis import Diagnosis
from app.models.evaluation import StudentEvaluation
from app.models.flash_card import FlashCard
from app.models.note import Note
from app.models.resource import ResourceFavorite
from app.models.user import User
from app.schemas.growth import (
    DashboardStatCard,
    EvaluationCreate,
    EvaluationResponse,
    EvaluationUpdate,
    GrowthDashboard,
    TimelineItem,
)


class GrowthService:
    """成长档案聚合服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== 评价 CRUD ==========

    async def create_evaluation(
        self,
        teacher_id: int,
        tenant_id: int,
        data: EvaluationCreate,
    ) -> EvaluationResponse:
        """创建学生评价"""
        ...

    async def get_evaluation(self, evaluation_id: int) -> Optional[EvaluationResponse]:
        """获取评价详情（含教师姓名、课程名称联表查询）"""
        ...

    async def list_evaluations(
        self,
        student_id: int,
        course_id: Optional[int] = None,
    ) -> Tuple[List[EvaluationResponse], int]:
        """获取学生评价列表，返回 (items, total)"""
        ...

    async def update_evaluation(
        self,
        evaluation_id: int,
        teacher_id: int,
        data: EvaluationUpdate,
    ) -> Optional[EvaluationResponse]:
        """更新评价（仅作者可操作）"""
        ...

    async def delete_evaluation(
        self,
        evaluation_id: int,
        teacher_id: int,
    ) -> bool:
        """删除评价（仅作者可操作）"""
        ...

    # ========== 时间线聚合 ==========

    async def get_timeline(
        self,
        student_id: int,
        source: Optional[str] = None,
    ) -> List[TimelineItem]:
        """
        聚合查询学生成长时间线

        数据源映射:
        - "evaluation" → StudentEvaluation
        - "agent"      → AgentSession (AI对话)
        - "diagnosis"  → Diagnosis (学习诊断)
        - "note"       → Note (笔记)
        - "flashcard"  → FlashCard (复习卡片)
        - "course"     → CourseEnrollment (选课/进度)
        - "resource"   → ResourceFavorite (资源收藏)
        - "classroom"  → ClassroomParticipant (课堂参与)

        各源查 page_size*2 条，合并排序后截取分页区间
        """
        ...

    async def _fetch_agent_sessions(self, student_id: int, limit: int) -> List[TimelineItem]:
        """查询 AI 对话记录"""
        ...

    async def _fetch_diagnoses(self, student_id: int, limit: int) -> List[TimelineItem]:
        """查询学习诊断记录"""
        ...

    async def _fetch_notes(self, student_id: int, limit: int) -> List[TimelineItem]:
        """查询笔记记录"""
        ...

    async def _fetch_flashcards(self, student_id: int, limit: int) -> List[TimelineItem]:
        """查询复习卡片记录"""
        ...

    async def _fetch_evaluations(self, student_id: int, limit: int) -> List[TimelineItem]:
        """查询教师评价记录"""
        ...

    async def _fetch_course_enrollments(self, student_id: int, limit: int) -> List[TimelineItem]:
        """查询选课记录"""
        ...

    async def _fetch_resource_favorites(self, student_id: int, limit: int) -> List[TimelineItem]:
        """查询资源收藏记录"""
        ...

    async def _fetch_classroom_participations(self, student_id: int, limit: int) -> List[TimelineItem]:
        """查询课堂参与记录"""
        ...

    # ========== 仪表盘 ==========

    async def get_dashboard(
        self,
        student_id: int,
    ) -> GrowthDashboard:
        """
        获取成长仪表盘数据

        统计:
        - stat_cards: AI对话数、诊断次数、笔记数、卡片数、课程数、评价数
        - weekly_activity: 近7天每日活动数 (从 ClickHouse 或 PG 聚合)
        - subject_distribution: 按学科分布的学习活动
        - recent_evaluations: 最近3条教师评价
        """
        ...

    async def _get_stat_cards(self, student_id: int) -> List[DashboardStatCard]:
        """获取统计卡片数据"""
        ...

    async def _get_weekly_activity(self, student_id: int) -> List[Dict[str, Any]]:
        """获取近7天活动趋势"""
        ...

    async def _get_subject_distribution(self, student_id: int) -> List[Dict[str, Any]]:
        """获取学科分布"""
        ...
```

### 3.5 前端组件设计

#### GrowthProfileView.vue（主页面）

```typescript
// Props
interface Props {
  // 通过路由参数获取，不需要显式 props
}

// 路由参数
// 学生端: /scene/:sceneType/growth-profile → 无 studentId 参数，使用当前用户
// 教师端: /teacher/students/:studentId/growth-profile → studentId 从路由参数获取

// 视角判断
const isTeacherView = computed(() => route.path.startsWith('/teacher/'))
const studentId = computed(() =>
  isTeacherView.value ? Number(route.params.studentId) : authStore.user?.id
)
```

#### GrowthTimeline.vue

```typescript
// Props
interface Props {
  items: TimelineItem[]      // 时间线条目列表
  loading: boolean           // 加载状态
  hasMore: boolean           // 是否还有更多
}

// Emits
interface Emits {
  (e: 'load-more'): void     // 加载更多
  (e: 'filter', source: string): void  // 筛选数据源
}
```

#### GrowthDashboard.vue

```typescript
// Props
interface Props {
  data: GrowthDashboard | null   // 仪表盘数据
  loading: boolean               // 加载状态
}

// Emits: 无（纯展示组件）
```

#### TeacherEvaluationCard.vue

```typescript
// Props
interface Props {
  evaluation: EvaluationResponse   // 评价数据
  editable: boolean                // 是否可编辑（教师视角且是作者）
}

// Emits
interface Emits {
  (e: 'edit', evaluation: EvaluationResponse): void   // 编辑评价
  (e: 'delete', evaluationId: number): void           // 删除评价
}
```

#### EvaluationForm.vue

```typescript
// Props
interface Props {
  visible: boolean                 // 对话框可见性
  evaluation?: EvaluationResponse  // 编辑时传入已有评价，新建时不传
  studentId: number                // 被评价学生ID
  courseId?: number                // 关联课程ID（可选）
}

// Emits
interface Emits {
  (e: 'update:visible', val: boolean): void  // v-model:visible
  (e: 'success', evaluation: EvaluationResponse): void  // 提交成功
}
```

---

## 4. 任务列表

按实现顺序排列，标注依赖关系。

| 任务编号 | 任务描述 | 涉及文件 | 依赖前置任务 |
|---------|---------|---------|-------------|
| T01 | 创建 StudentEvaluation 模型 | B1, B2 | 无 |
| T02 | 创建 Alembic 迁移脚本 | B7 | T01 |
| T03 | 执行迁移，验证表结构 | B7 | T02 |
| T04 | 创建 Pydantic Schemas | B3 | T01 |
| T05 | 创建 GrowthService（评价 CRUD 部分） | B4 | T01, T04 |
| T06 | 创建 Growth API 路由（评价端点） | B5, B6 | T04, T05 |
| T07 | 实现 GrowthService 时间线聚合方法 | B4 | T01, T04 |
| T08 | 实现 GrowthService 仪表盘聚合方法 | B4 | T01, T04 |
| T09 | 创建 Growth API 路由（时间线 + 仪表盘端点） | B5, B6 | T07, T08 |
| T10 | 后端联调测试（API 全流程验证） | B5 | T06, T09 |
| T11 | 创建前端 API 服务 `growth.ts` | F1 | T06, T09 |
| T12 | 创建前端 Pinia Store `growth.ts` | F2 | F1 |
| T13 | 实现 GrowthDashboard 组件 | F5 | F1 |
| T14 | 实现 GrowthTimeline 组件 | F4 | F1 |
| T15 | 实现 TeacherEvaluationCard 组件 | F6 | F1 |
| T16 | 实现 EvaluationForm 组件 | F7 | F1 |
| T17 | 实现 GrowthProfileView 主页面 | F3 | F12, F13, F14, F15, F16 |
| T18 | 添加前端路由（学生端 + 教师端） | F8, F9 | F17 |
| T19 | 添加侧边栏菜单项 | F10 | F18 |
| T20 | 前端联调测试（全流程验证） | F3 | T18, T19 |

**依赖关系图**：

```
T01 → T02 → T03
 ↓
T04 → T05 → T06 → T10
 ↓         ↓
T07   T08 → T09 → T10
           ↓
     T11 → T12 → T17 ← T13, T14, T15, T16
                       ↓
                 T18 → T19 → T20
```

**关键路径**：T01 → T04 → T05 → T06 → T10 → T11 → T12 → T17 → T18 → T19 → T20

**建议并行**：
- T07/T08 可与 T05/T06 并行（都依赖 T04）
- T13/T14/T15/T16 可并行（都依赖 T11）

---

## 5. 依赖包列表

### 5.1 后端 pip 包

**无需新增**。所需依赖均已存在于项目中：
- `sqlalchemy[asyncio]` — ORM
- `pydantic` — Schema 验证
- `fastapi` — API 框架
- `httpx` — ClickHouse HTTP 查询（已有）
- `alembic` — 迁移

### 5.2 前端 npm 包

| 包名 | 版本 | 用途 | 安装命令 |
|------|------|------|---------|
| `echarts` | `^5.5.0` | 仪表盘图表（饼图/柱状图/折线图） | `npm install echarts` |
| `vue-echarts` | `^7.0.0` | Vue3 ECharts 封装组件 | `npm install vue-echarts` |

> **注意**：如果项目中已安装 echarts 则跳过。安装前请执行 `grep '"echarts"' frontend/package.json` 检查。

---

## 6. 共享知识（跨文件约定）

### 6.1 API 响应格式

**统一响应体**（使用 `app/schemas/common.py` 中的 `APIResponse`）：

```json
// 成功
{
  "code": 200,
  "data": { ... },
  "message": "success"
}

// 失败
{
  "code": 1002,
  "data": null,
  "message": "权限不足"
}
```

> **约定**：本模块 API 统一使用 `APIResponse(data=result)` 构造成功响应（code 默认 200，message 默认 "success"）。与 diagnosis 模块使用 `code=0` 不同，本模块遵循 common.py 定义的默认值 200。

### 6.2 分页约定

**请求参数**（Query）：

```
page: int = 1       # 页码，从1开始
page_size: int = 20  # 每页数量
```

**响应格式**（使用 `PaginatedResponse`）：

```json
{
  "code": 200,
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "message": "success"
}
```

### 6.3 错误处理

| HTTP 状态码 | 场景 | 响应 |
|------------|------|------|
| 400 | 参数校验失败 | `{"code": 1001, "message": "参数错误: ...", "data": null}` |
| 401 | 未认证 / Token 过期 | `{"detail": "Token无效或已过期"}` |
| 403 | 权限不足（学生访问他人档案、非作者修改评价） | `{"code": 1002, "message": "权限不足", "data": null}` |
| 404 | 评价不存在 | `{"detail": "评价不存在"}` |
| 500 | 服务器内部错误 | `{"detail": "服务器内部错误"}` |

**后端错误处理模式**：

```python
# 404 - 资源不存在
raise HTTPException(status_code=404, detail="评价不存在")

# 403 - 权限不足
raise HTTPException(status_code=403, detail="权限不足")

# 400 - 参数错误
raise HTTPException(status_code=400, detail="评分必须在1-5之间")
```

### 6.4 前端 API 调用约定

**服务文件模式**（参照 `services/note.ts`）：

```typescript
// services/growth.ts
import api from './api'

// 类型定义
export interface EvaluationItem { ... }
export interface TimelineItem { ... }
export interface GrowthDashboardData { ... }

// API 对象
export const growthApi = {
  async createEvaluation(params: EvaluationCreateParams): Promise<EvaluationItem> {
    const response = await api.post('/growth/evaluations', params)
    return response.data as EvaluationItem
  },
  async getTimeline(params: TimelineParams): Promise<PaginatedTimeline> {
    const response = await api.get('/growth/timeline', { params })
    return response.data as PaginatedTimeline
  },
  // ...
}
```

**响应拦截器约定**：
- `api.ts` 响应拦截器已处理 `code !== 200 && code !== 0` 的情况，自动 `ElMessage.error()`
- 前端 service 方法直接 `return response.data`，由拦截器保证成功时 `data` 为有效数据
- 错误由拦截器统一 toast，业务代码只需 `try/catch` 处理 UI 状态

### 6.5 前端 Store 约定

**Setup Store 模式**（参照 `stores/note.ts`）：

```typescript
// stores/growth.ts
export const useGrowthStore = defineStore('growth', () => {
  // State
  const dashboard = ref<GrowthDashboardData | null>(null)
  const timeline = ref<TimelineItem[]>([])
  const evaluations = ref<EvaluationItem[]>([])
  const isLoading = ref(false)
  const timelineHasMore = ref(true)

  // Getters
  const recentEvaluations = computed(() =>
    evaluations.value.slice(0, 3)
  )

  // Actions
  async function fetchDashboard(studentId: number) { ... }
  async function fetchTimeline(studentId: number, page: number) { ... }
  async function createEvaluation(params: ...) { ... }

  return { dashboard, timeline, evaluations, isLoading, ... }
})
```

### 6.6 路由约定

**学生端路由**（添加到 `scene-routes.ts`）：

```typescript
{
  path: 'growth-profile',
  name: 'GrowthProfile',
  component: () => import('@/views/growth/GrowthProfileView.vue'),
  meta: {
    title: '成长档案',
    requiresAuth: true,
    allowedRoles: ['student', 'teacher', 'admin'],
  },
},
```

**教师端路由**（添加到 `teacher-routes.ts`）：

```typescript
{
  path: 'students/:studentId/growth-profile',
  name: 'TeacherStudentGrowthProfile',
  component: () => import('@/views/growth/GrowthProfileView.vue'),
  meta: {
    title: '学生成长档案',
    requiresAuth: true,
    roles: ['teacher', 'admin'],
  },
},
```

### 6.7 侧边栏菜单约定

在 `Sidebar.vue` 的 `featureMenus` 中添加：

```typescript
{ index: `/scene/${currentSceneType.value}/growth-profile`, icon: 'TrendCharts', title: '成长档案' },
```

---

## 7. 待明确事项

| # | 问题 | 影响范围 | 建议方案 | 状态 |
|---|------|---------|---------|------|
| 1 | **ClickHouse 数据源是否纳入时间线？** | GrowthService 时间线聚合 | 当前方案仅从 PostgreSQL 聚合（7个数据源），ClickHouse `AnalyticsEvent` 暂不纳入时间线，仅用于仪表盘的 `weekly_activity` 趋势图。若需纳入需在 `_fetch_clickhouse_events()` 中处理 HTTP 查询，增加延迟。 | 待确认 |
| 2 | **评价是否支持附件/图片？** | StudentEvaluation 模型、EvaluationForm 组件 | 当前方案不支持附件。如需支持，需增加 `attachment_urls` 字段（JSON 数组），前端 EvaluationForm 添加上传组件。 | 待确认 |
| 3 | **学生能否回复教师评价？** | 数据模型、API、前端组件 | 当前方案为单向评价（教师→学生）。如需双向互动，需新增 `EvaluationReply` 模型或在现有模型增加 `student_reply` 字段。 | 待确认 |
| 4 | **时间线是否需要导出功能？** | GrowthService、前端组件 | 当前方案不含导出。可复用现有 `export_service.py` 模式，生成 PDF/Markdown 成长报告。建议作为 P1 需求后续迭代。 | 待确认 |
| 5 | **仪表盘的 `weekly_activity` 数据来源** | GrowthService._get_weekly_activity() | 方案 A：从 ClickHouse 查询 `AnalyticsEvent`（准确但依赖 ClickHouse 可用性）；方案 B：从 PostgreSQL 各表按 `created_at` 聚合（近似但可靠）。当前建议方案 B，ClickHouse 可选增强。 | 待确认 |
| 6 | **教师评价是否关联到课堂/课时？** | 数据模型 | 当前 `course_id` 可选关联课程。若需关联到具体课堂，需增加 `classroom_id` 字段。 | 待确认 |
| 7 | **ECharts 是否已在项目中安装？** | 前端构建 | 需检查 `frontend/package.json`。若未安装需执行 `npm install echarts vue-echarts`。若已安装其他图表库（如 Chart.js）则统一使用已有库。 | 待确认 |

---

## 附录 A：数据源映射表

| source 标识 | ORM 模型 | 时间字段 | 事件类型 | 标题字段 |
|------------|---------|---------|---------|---------|
| `evaluation` | `StudentEvaluation` | `created_at` | `teacher_evaluation` | `evaluation_type` + `rating` |
| `agent` | `AgentSession` | `created_at` | `ai_chat` | `title` / `agent_type` |
| `diagnosis` | `Diagnosis` | `completed_at` / `created_at` | `diagnosis_completed` | `title` |
| `note` | `Note` | `created_at` | `note_created` | `title` |
| `flashcard` | `FlashCard` | `created_at` | `flashcard_created` | `knowledge_point` / `front[:30]` |
| `course` | `CourseEnrollment` | `enrolled_at` | `course_enrolled` | 关联 Course.name |
| `resource` | `ResourceFavorite` | `created_at` | `resource_favorited` | 关联 Resource.title |
| `classroom` | `ClassroomParticipant` | `joined_at` | `classroom_joined` | 关联 Classroom.title |

## 附录 B：仪表盘统计卡片定义

| key | label | 数据源 | 查询 |
|-----|-------|-------|------|
| `ai_chat_count` | AI对话数 | AgentSession | `COUNT(*) WHERE user_id = :student_id` |
| `diagnosis_count` | 诊断次数 | Diagnosis | `COUNT(*) WHERE user_id = :student_id` |
| `note_count` | 笔记数 | Note | `COUNT(*) WHERE owner_id = :student_id AND is_deleted = false` |
| `flashcard_count` | 复习卡片 | FlashCard | `COUNT(*) WHERE user_id = :student_id AND is_active = true` |
| `course_count` | 已选课程 | CourseEnrollment | `COUNT(*) WHERE user_id = :student_id AND dropped_at IS NULL` |
| `evaluation_count` | 教师评价 | StudentEvaluation | `COUNT(*) WHERE student_id = :student_id AND is_visible = true` |
| `resource_favorite_count` | 收藏资源 | ResourceFavorite | `COUNT(*) WHERE user_id = :student_id` |
| `classroom_count` | 课堂参与 | ClassroomParticipant | `COUNT(*) WHERE user_id = :student_id` |
