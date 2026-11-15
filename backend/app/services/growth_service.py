"""
智慧学伴 学生成长档案服务
评价 CRUD、时间线聚合查询、仪表盘数据聚合
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentSession
from app.models.classroom import Classroom, ClassroomParticipant
from app.models.course import Course, CourseEnrollment
from app.models.diagnosis import Diagnosis
from app.models.evaluation import StudentEvaluation
from app.models.flash_card import FlashCard
from app.models.note import Note
from app.models.resource import Resource, ResourceFavorite
from app.models.user import User
from app.schemas.growth import (
    DashboardStatCard,
    EvaluationCreate,
    EvaluationResponse,
    EvaluationUpdate,
    GrowthDashboard,
    TimelineItem,
)

logger = logging.getLogger(__name__)


class GrowthService:
    """学生成长档案服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 评价 CRUD
    # ------------------------------------------------------------------

    async def create_evaluation(
        self,
        teacher_id: int,
        tenant_id: int,
        data: EvaluationCreate,
    ) -> EvaluationResponse:
        """创建学生评价"""
        evaluation = StudentEvaluation(
            tenant_id=tenant_id,
            student_id=data.student_id,
            teacher_id=teacher_id,
            course_id=data.course_id,
            evaluation_type=data.evaluation_type,
            rating=data.rating,
            content=data.content,
            suggestion=data.suggestion,
            is_visible=data.is_visible,
        )
        self.db.add(evaluation)
        await self.db.flush()

        # 查询教师姓名
        teacher_result = await self.db.execute(
            select(User.nickname).where(User.id == teacher_id)
        )
        teacher_name = teacher_result.scalar() or "未知"

        # 查询课程名称
        course_name: Optional[str] = None
        if data.course_id:
            course_result = await self.db.execute(
                select(Course.name).where(Course.id == data.course_id)
            )
            course_name = course_result.scalar()

        return self._to_response(evaluation, teacher_name, course_name)

    async def get_evaluation(
        self,
        evaluation_id: int,
    ) -> Optional[EvaluationResponse]:
        """获取评价详情（联表查询教师姓名和课程名称）"""
        stmt = (
            select(StudentEvaluation, User.nickname, Course.name)
            .join(User, StudentEvaluation.teacher_id == User.id)
            .outerjoin(Course, StudentEvaluation.course_id == Course.id)
            .where(StudentEvaluation.id == evaluation_id)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            return None

        evaluation, teacher_name, course_name = row
        return self._to_response(evaluation, teacher_name, course_name)

    async def list_evaluations(
        self,
        student_id: int,
        course_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[EvaluationResponse], int]:
        """获取学生评价列表"""
        conditions = [StudentEvaluation.student_id == student_id]
        if course_id is not None:
            conditions.append(StudentEvaluation.course_id == course_id)

        # 总数
        count_stmt = select(func.count()).select_from(StudentEvaluation).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 分页查询（联表）
        offset = (page - 1) * page_size
        stmt = (
            select(StudentEvaluation, User.nickname, Course.name)
            .join(User, StudentEvaluation.teacher_id == User.id)
            .outerjoin(Course, StudentEvaluation.course_id == Course.id)
            .where(and_(*conditions))
            .order_by(desc(StudentEvaluation.created_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        items = [
            self._to_response(ev, teacher_name, course_name)
            for ev, teacher_name, course_name in rows
        ]
        return items, total

    async def update_evaluation(
        self,
        evaluation_id: int,
        teacher_id: int,
        data: EvaluationUpdate,
    ) -> Optional[EvaluationResponse]:
        """更新评价（仅作者）"""
        stmt = select(StudentEvaluation).where(StudentEvaluation.id == evaluation_id)
        result = await self.db.execute(stmt)
        evaluation = result.scalars().first()

        if not evaluation:
            return None
        if evaluation.teacher_id != teacher_id:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        for key, value in update_fields.items():
            setattr(evaluation, key, value)

        await self.db.flush()

        # 查询联表信息
        join_stmt = (
            select(User.nickname, Course.name)
            .outerjoin(Course, StudentEvaluation.course_id == Course.id)
            .join(User, StudentEvaluation.teacher_id == User.id)
            .where(StudentEvaluation.id == evaluation_id)
        )
        join_result = await self.db.execute(join_stmt)
        row = join_result.first()
        teacher_name = row[0] if row else "未知"
        course_name = row[1] if row else None

        return self._to_response(evaluation, teacher_name, course_name)

    async def delete_evaluation(
        self,
        evaluation_id: int,
        teacher_id: int,
    ) -> bool:
        """删除评价（仅作者）"""
        stmt = select(StudentEvaluation).where(StudentEvaluation.id == evaluation_id)
        result = await self.db.execute(stmt)
        evaluation = result.scalars().first()

        if not evaluation:
            return False
        if evaluation.teacher_id != teacher_id:
            return False

        await self.db.delete(evaluation)
        await self.db.flush()
        return True

    # ------------------------------------------------------------------
    # 时间线聚合
    # ------------------------------------------------------------------

    async def get_timeline(
        self,
        student_id: int,
        source: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TimelineItem], int]:
        """获取学生成长时间线"""
        source_map = {
            "agent": self._fetch_agent_sessions,
            "diagnosis": self._fetch_diagnoses,
            "note": self._fetch_notes,
            "flashcard": self._fetch_flashcards,
            "evaluation": self._fetch_evaluations,
            "course": self._fetch_course_enrollments,
            "resource": self._fetch_resource_favorites,
            "classroom": self._fetch_classroom_participations,
        }

        if source and source in source_map:
            items = await source_map[source](student_id)
        else:
            # 并行查询所有数据源
            tasks = [fetcher(student_id) for fetcher in source_map.values()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            items: List[TimelineItem] = []
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("时间线查询失败: %s", result)
                    continue
                items.extend(result)

        # 按时间倒序排序
        items.sort(key=lambda x: x.timestamp, reverse=True)

        # 分页
        total = len(items)
        offset = (page - 1) * page_size
        paged_items = items[offset : offset + page_size]
        return paged_items, total

    async def _fetch_agent_sessions(self, student_id: int) -> List[TimelineItem]:
        """查询 AI 对话会话"""
        stmt = (
            select(AgentSession)
            .where(AgentSession.user_id == student_id)
            .order_by(desc(AgentSession.created_at))
            .limit(50)
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()

        return [
            TimelineItem(
                source="agent",
                event_type="ai_chat",
                title=s.title or f"{s.agent_type}对话",
                description=f"{s.message_count}条消息",
                timestamp=s.created_at,
                metadata={"session_id": s.id, "agent_type": s.agent_type},
            )
            for s in sessions
        ]

    async def _fetch_diagnoses(self, student_id: int) -> List[TimelineItem]:
        """查询学习诊断"""
        stmt = (
            select(Diagnosis)
            .where(Diagnosis.user_id == student_id)
            .order_by(desc(Diagnosis.created_at))
            .limit(50)
        )
        result = await self.db.execute(stmt)
        diagnoses = result.scalars().all()

        return [
            TimelineItem(
                source="diagnosis",
                event_type="diagnosis_completed",
                title=d.title,
                description=f"得分: {d.score}" if d.score is not None else None,
                timestamp=d.completed_at or d.created_at,
                metadata={"score": d.score, "diagnosis_id": d.id},
            )
            for d in diagnoses
        ]

    async def _fetch_notes(self, student_id: int) -> List[TimelineItem]:
        """查询笔记"""
        stmt = (
            select(Note)
            .where(and_(Note.owner_id == student_id, Note.is_deleted == False))
            .order_by(desc(Note.created_at))
            .limit(50)
        )
        result = await self.db.execute(stmt)
        notes = result.scalars().all()

        return [
            TimelineItem(
                source="note",
                event_type="note_created",
                title=n.title,
                description=f"{n.word_count}字",
                timestamp=n.created_at,
                metadata={"note_id": n.id},
            )
            for n in notes
        ]

    async def _fetch_flashcards(self, student_id: int) -> List[TimelineItem]:
        """查询复习卡片"""
        stmt = (
            select(FlashCard)
            .where(and_(FlashCard.user_id == student_id, FlashCard.is_active == True))
            .order_by(desc(FlashCard.created_at))
            .limit(50)
        )
        result = await self.db.execute(stmt)
        cards = result.scalars().all()

        return [
            TimelineItem(
                source="flashcard",
                event_type="flashcard_created",
                title=c.knowledge_point or (c.front[:30] if c.front else "复习卡片"),
                description=f"复习{c.repetition_count}次",
                timestamp=c.created_at,
            )
            for c in cards
        ]

    async def _fetch_evaluations(self, student_id: int) -> List[TimelineItem]:
        """查询教师评价"""
        stmt = (
            select(StudentEvaluation)
            .where(
                and_(
                    StudentEvaluation.student_id == student_id,
                    StudentEvaluation.is_visible == True,
                )
            )
            .order_by(desc(StudentEvaluation.created_at))
            .limit(50)
        )
        result = await self.db.execute(stmt)
        evals = result.scalars().all()

        return [
            TimelineItem(
                source="evaluation",
                event_type="teacher_evaluation",
                title=f"教师评价·{e.evaluation_type}",
                description=e.content[:100] if e.content else None,
                timestamp=e.created_at,
                metadata={"rating": e.rating},
            )
            for e in evals
        ]

    async def _fetch_course_enrollments(self, student_id: int) -> List[TimelineItem]:
        """查询课程选课（联表查课程名称）"""
        stmt = (
            select(CourseEnrollment, Course.name)
            .join(Course, CourseEnrollment.course_id == Course.id)
            .where(
                and_(
                    CourseEnrollment.user_id == student_id,
                    CourseEnrollment.dropped_at.is_(None),
                )
            )
            .order_by(desc(CourseEnrollment.enrolled_at))
            .limit(50)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            TimelineItem(
                source="course",
                event_type="course_enrolled",
                title=course_name,
                description=f"进度{enrollment.progress}%",
                timestamp=enrollment.enrolled_at,
            )
            for enrollment, course_name in rows
        ]

    async def _fetch_resource_favorites(self, student_id: int) -> List[TimelineItem]:
        """查询资源收藏（联表查资源标题）"""
        stmt = (
            select(ResourceFavorite, Resource.title)
            .join(Resource, ResourceFavorite.resource_id == Resource.id)
            .where(ResourceFavorite.user_id == student_id)
            .order_by(desc(ResourceFavorite.created_at))
            .limit(50)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            TimelineItem(
                source="resource",
                event_type="resource_favorited",
                title=resource_title,
                timestamp=favorite.created_at,
            )
            for favorite, resource_title in rows
        ]

    async def _fetch_classroom_participations(self, student_id: int) -> List[TimelineItem]:
        """查询课堂参与（联表查课堂标题）"""
        stmt = (
            select(ClassroomParticipant, Classroom.title)
            .join(Classroom, ClassroomParticipant.classroom_id == Classroom.id)
            .where(ClassroomParticipant.user_id == student_id)
            .order_by(desc(ClassroomParticipant.joined_at))
            .limit(50)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            TimelineItem(
                source="classroom",
                event_type="classroom_joined",
                title=classroom_title,
                timestamp=participant.joined_at,
            )
            for participant, classroom_title in rows
        ]

    # ------------------------------------------------------------------
    # 仪表盘聚合
    # ------------------------------------------------------------------

    async def get_dashboard(self, student_id: int) -> GrowthDashboard:
        """获取成长仪表盘数据"""
        stat_cards, weekly_activity, subject_distribution, recent_evaluations = await asyncio.gather(
            self._get_stat_cards(student_id),
            self._get_weekly_activity(student_id),
            self._get_subject_distribution(student_id),
            self._get_recent_evaluations(student_id),
        )
        return GrowthDashboard(
            stat_cards=stat_cards,
            weekly_activity=weekly_activity,
            subject_distribution=subject_distribution,
            recent_evaluations=recent_evaluations,
        )

    async def _get_stat_cards(self, student_id: int) -> List[DashboardStatCard]:
        """并行 COUNT 查询 8 个数据源"""
        (
            agent_count,
            diagnosis_count,
            note_count,
            flashcard_count,
            evaluation_count,
            course_count,
            resource_count,
            classroom_count,
        ) = await asyncio.gather(
            self._count(AgentSession, AgentSession.user_id == student_id),
            self._count(Diagnosis, Diagnosis.user_id == student_id),
            self._count(Note, and_(Note.owner_id == student_id, Note.is_deleted == False)),
            self._count(FlashCard, and_(FlashCard.user_id == student_id, FlashCard.is_active == True)),
            self._count(StudentEvaluation, and_(StudentEvaluation.student_id == student_id, StudentEvaluation.is_visible == True)),
            self._count(CourseEnrollment, and_(CourseEnrollment.user_id == student_id, CourseEnrollment.dropped_at.is_(None))),
            self._count(ResourceFavorite, ResourceFavorite.user_id == student_id),
            self._count(ClassroomParticipant, ClassroomParticipant.user_id == student_id),
        )

        return [
            DashboardStatCard(key="ai_chat", label="AI对话", value=agent_count, icon="chat"),
            DashboardStatCard(key="diagnosis", label="学习诊断", value=diagnosis_count, icon="clipboard"),
            DashboardStatCard(key="note", label="笔记", value=note_count, icon="note"),
            DashboardStatCard(key="flashcard", label="复习卡片", value=flashcard_count, icon="card"),
            DashboardStatCard(key="evaluation", label="教师评价", value=evaluation_count, icon="star"),
            DashboardStatCard(key="course", label="已选课程", value=course_count, icon="book"),
            DashboardStatCard(key="resource", label="收藏资源", value=resource_count, icon="bookmark"),
            DashboardStatCard(key="classroom", label="课堂参与", value=classroom_count, icon="users"),
        ]

    async def _count(self, model: Any, condition: Any) -> int:
        """通用 COUNT 查询"""
        stmt = select(func.count()).select_from(model).where(condition)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _get_weekly_activity(self, student_id: int) -> List[Dict[str, Any]]:
        """近 7 天每日活动统计"""
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        # 定义各数据源查询参数: (model, user_column, source_key, extra_conditions)
        sources = [
            (AgentSession, AgentSession.user_id, "agent", []),
            (Diagnosis, Diagnosis.user_id, "diagnosis", []),
            (Note, Note.owner_id, "note", [Note.is_deleted == False]),
            (FlashCard, FlashCard.user_id, "flashcard", [FlashCard.is_active == True]),
            (StudentEvaluation, StudentEvaluation.student_id, "evaluation", [StudentEvaluation.is_visible == True]),
        ]

        # 并行查询各数据源
        async def query_source(model, user_col, source_key, extra_conds):
            conditions = [user_col == student_id, model.created_at >= seven_days_ago] + extra_conds
            stmt = (
                select(
                    func.date(model.created_at).label("day"),
                    func.count().label("count"),
                )
                .where(and_(*conditions))
                .group_by(func.date(model.created_at))
            )
            result = await self.db.execute(stmt)
            return {str(row.day): row.count for row in result}

        source_maps = await asyncio.gather(
            *[query_source(*params) for params in sources]
        )

        # 构建近 7 天每日数据
        source_keys = [params[2] for params in sources]
        days: List[Dict[str, Any]] = []
        for i in range(7):
            day = (datetime.utcnow() - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            day_data: Dict[str, Any] = {"date": day}
            total = 0
            for source_key, source_map in zip(source_keys, source_maps):
                count = source_map.get(day, 0)
                day_data[source_key] = count
                total += count
            day_data["total"] = total
            days.append(day_data)

        return days

    async def _get_subject_distribution(self, student_id: int) -> List[Dict[str, Any]]:
        """学科分布 — 从选课表联表课程表按学科分组"""
        stmt = (
            select(Course.subject, func.count().label("count"))
            .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .where(
                and_(
                    CourseEnrollment.user_id == student_id,
                    CourseEnrollment.dropped_at.is_(None),
                )
            )
            .group_by(Course.subject)
        )
        result = await self.db.execute(stmt)
        return [
            {"subject": row.subject, "count": row.count}
            for row in result
        ]

    async def _get_recent_evaluations(self, student_id: int) -> List[EvaluationResponse]:
        """最近评价（取 5 条）"""
        items, _ = await self.list_evaluations(student_id, page=1, page_size=5)
        return items

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _to_response(
        evaluation: StudentEvaluation,
        teacher_name: str,
        course_name: Optional[str],
    ) -> EvaluationResponse:
        """将 ORM 对象转换为 EvaluationResponse"""
        return EvaluationResponse(
            id=evaluation.id,
            student_id=evaluation.student_id,
            teacher_id=evaluation.teacher_id,
            teacher_name=teacher_name,
            course_id=evaluation.course_id,
            course_name=course_name,
            evaluation_type=evaluation.evaluation_type,
            rating=evaluation.rating,
            content=evaluation.content,
            suggestion=evaluation.suggestion,
            is_visible=evaluation.is_visible,
            created_at=evaluation.created_at,
            updated_at=evaluation.updated_at,
        )
