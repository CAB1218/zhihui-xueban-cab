"""
AI4Edu 教师工作台服务
班级概览、学生分析、备课管理
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.lesson_plan_agent import LessonPlanAgent
from app.core.exceptions import NotFoundException, PermissionDeniedException
from app.models.lesson_plan import LessonPlan
from app.models.course import Course, CourseEnrollment
from app.models.resource import Resource
from app.models.user import User
from app.models.diagnosis import Diagnosis
from app.schemas.common import PaginatedResponse, PaginationParams

logger = logging.getLogger(__name__)


class TeacherService:
    """教师工作台服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_dashboard(
        self,
        tenant_id: int,
        teacher_id: int,
    ) -> Dict[str, Any]:
        """
        获取教师仪表盘数据

        Args:
            tenant_id: 租户ID
            teacher_id: 教师ID

        Returns:
            仪表盘数据
        """
        # 教案统计
        plan_count_stmt = select(func.count(LessonPlan.id)).where(
            and_(
                LessonPlan.teacher_id == teacher_id,
                LessonPlan.tenant_id == tenant_id,
                LessonPlan.is_active == True,
            )
        )
        plan_count_result = await self.db.execute(plan_count_stmt)
        plan_count = plan_count_result.scalar() or 0

        # 最近教案
        recent_plans_stmt = (
            select(LessonPlan)
            .where(
                and_(
                    LessonPlan.teacher_id == teacher_id,
                    LessonPlan.tenant_id == tenant_id,
                    LessonPlan.is_active == True,
                )
            )
            .order_by(desc(LessonPlan.updated_at))
            .limit(5)
        )
        recent_plans_result = await self.db.execute(recent_plans_stmt)
        recent_plans = recent_plans_result.scalars().all()

        # 课程数：与 list_courses 同口径（租户内启用课程），避免「卡片 0 门 / 列表 4 门」自相矛盾
        course_count_stmt = select(func.count(Course.id)).where(
            and_(Course.tenant_id == tenant_id, Course.is_active == True)
        )
        course_count = (await self.db.execute(course_count_stmt)).scalar() or 0

        student_count_stmt = (
            select(func.count(func.distinct(CourseEnrollment.user_id)))
            .join(Course, Course.id == CourseEnrollment.course_id)
            .where(
                and_(
                    Course.tenant_id == tenant_id,
                    Course.is_active == True,
                    CourseEnrollment.dropped_at.is_(None),
                )
            )
        )
        student_count = (await self.db.execute(student_count_stmt)).scalar() or 0

        resource_count_stmt = select(func.count(Resource.id)).where(
            and_(Resource.tenant_id == tenant_id, Resource.uploader_id == teacher_id, Resource.is_active == True)
        )
        resource_count = (await self.db.execute(resource_count_stmt)).scalar() or 0

        return {
            "teacher_id": teacher_id,
            "lesson_plan_count": plan_count,
            "student_count": student_count,
            "course_count": course_count,
            "resource_count": resource_count,
            "recent_lesson_plans": [
                {
                    "id": p.id,
                    "title": p.title,
                    "status": p.status,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in recent_plans
            ],
        }

    async def list_courses(self, tenant_id: int, teacher_id: int) -> List[Dict[str, Any]]:
        """Return the courses a teacher can use in this tenant.

        之前只返回 ``teacher_id == 本人`` 的课程，导致「接管别人课程」或
        「课程都建在管理员名下」的教师在下拉里看到「无数据」，既不能发起课堂，
        也进不了班级诊断。现在改为返回租户内全部启用课程，本人课程排在前面，
        并用 ``owned`` 标记归属，前端可按需区分「我的课程」和「共享课程」。
        """
        stmt = (
            select(Course)
            .where(and_(Course.tenant_id == tenant_id, Course.is_active == True))
            .order_by(
                case((Course.teacher_id == teacher_id, 0), else_=1),
                desc(Course.updated_at),
            )
        )
        courses = (await self.db.execute(stmt)).scalars().all()
        return [
            {
                "id": course.id,
                "name": course.name,
                "subject": course.subject,
                "grade": course.grade,
                "semester": course.semester,
                "description": course.description,
                "teacher_id": course.teacher_id,
                "owned": course.teacher_id == teacher_id,
            }
            for course in courses
        ]

    async def list_lesson_plans(
        self,
        tenant_id: int,
        teacher_id: int,
        pagination: PaginationParams,
        course_id: Optional[int] = None,
    ) -> PaginatedResponse:
        """
        获取教案列表

        Args:
            tenant_id: 租户ID
            teacher_id: 教师ID
            pagination: 分页参数
            course_id: 课程ID筛选

        Returns:
            分页教案列表
        """
        conditions = [
            LessonPlan.teacher_id == teacher_id,
            LessonPlan.tenant_id == tenant_id,
            LessonPlan.is_active == True,
        ]

        if course_id:
            conditions.append(LessonPlan.course_id == course_id)

        # 总数
        count_stmt = select(func.count(LessonPlan.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 数据
        stmt = (
            select(LessonPlan)
            .where(and_(*conditions))
            .order_by(desc(LessonPlan.updated_at))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        result = await self.db.execute(stmt)
        plans = result.scalars().all()

        items = [
            {
                "id": p.id,
                "title": p.title,
                "course_id": p.course_id,
                "duration_minutes": p.duration_minutes,
                "ai_generated": p.ai_generated,
                "status": p.status,
                "version": p.version,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in plans
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def generate_lesson_plan_preview(
        self,
        course_name: str,
        objectives: Optional[str],
        knowledge_points: List[str],
        duration: int,
        student_level: str,
        user_id: int,
        tenant_id: int,
    ) -> Dict[str, Any]:
        """Generate a structured preview without persisting a lesson plan."""
        objective_text = (objectives or "").replace("。", "\n").replace("；", "\n")
        objective_list = [item.strip() for item in objective_text.splitlines() if item.strip()]
        if not objective_list:
            objective_list = [
                "理解课程核心概念",
                "掌握关键知识与方法",
                "能够运用所学知识解决问题",
            ]

        level_map = {
            "beginner": "基础",
            "intermediate": "中等",
            "advanced": "进阶",
        }
        try:
            agent = LessonPlanAgent()
            generated = await agent.generate_lesson_plan(
                title=course_name,
                subject=course_name,
                duration_minutes=duration,
                objectives=objective_list,
                key_points=knowledge_points,
                student_level=level_map.get(student_level, student_level),
                context={"user_id": user_id, "tenant_id": tenant_id},
            )
            generated_content = str(generated.get("content") or "").strip()
        except Exception as exc:
            logger.warning("lesson_plan_preview_fallback: %s", exc)
            generated_content = ""

        if generated_content:
            steps = [{
                "title": "AI生成教学方案",
                "duration": duration,
                "content": generated_content,
            }]
        else:
            steps = [
                {"title": "导入新课", "duration": 10, "content": "通过真实情境引入主题，建立新旧知识联系。"},
                {"title": "概念讲解", "duration": max(15, duration // 3), "content": "讲解核心概念，并结合示例帮助学生形成理解。"},
                {"title": "互动练习", "duration": max(10, duration // 4), "content": "安排分层练习与讨论，及时检查学习效果。"},
                {"title": "总结提升", "duration": 10, "content": "回顾重点，组织学生归纳知识结构并提出问题。"},
            ]

        return {
            "title": f"{course_name} — 教案",
            "objectives": objective_list,
            "steps": steps,
            "homework": ["完成本节课配套练习", "整理本节课知识框架"],
        }

    async def get_or_create_course(
        self,
        tenant_id: int,
        teacher_id: int,
        course_name: str,
    ) -> int:
        """Resolve a teacher course by name, creating a minimal course when needed."""
        stmt = select(Course).where(
            and_(
                Course.tenant_id == tenant_id,
                Course.teacher_id == teacher_id,
                Course.name == course_name,
                Course.is_active == True,
            )
        )
        existing = (await self.db.execute(stmt)).scalars().first()
        if existing:
            return existing.id

        lower_name = course_name.lower()
        subject_aliases = {
            "math": ("数学", "微积分", "代数", "几何", "math"),
            "physics": ("物理", "physics"),
            "chemistry": ("化学", "chemistry"),
            "biology": ("生物", "biology"),
            "cs": ("计算机", "编程", "算法", "computer"),
            "chinese": ("语文", "中文", "chinese"),
            "english": ("英语", "english"),
            "history": ("历史", "history"),
            "geography": ("地理", "geography"),
            "politics": ("政治", "politics"),
            "pe": ("体育", "physical education"),
            "art": ("艺术", "美术", "art"),
        }
        subject = "general"
        for subject_id, aliases in subject_aliases.items():
            if any(alias.lower() in lower_name for alias in aliases):
                subject = subject_id
                break

        now = datetime.utcnow()
        semester = f"{now.year}-{'spring' if now.month <= 7 else 'fall'}"
        course = Course(
            tenant_id=tenant_id,
            name=course_name,
            subject=subject,
            grade="未设置",
            semester=semester,
            description="由AI备课助手在保存教案时自动创建",
            teacher_id=teacher_id,
            is_active=True,
        )
        self.db.add(course)
        await self.db.flush()
        return course.id

    async def create_lesson_plan(
        self,
        tenant_id: int,
        teacher_id: int,
        course_id: int,
        title: str,
        objectives: Optional[List[str]] = None,
        content: Optional[str] = None,
        materials: Optional[List[str]] = None,
        duration_minutes: int = 45,
        ai_generated: bool = False,
    ) -> Dict[str, Any]:
        """
        创建教案

        Args:
            tenant_id: 租户ID
            teacher_id: 教师ID
            course_id: 课程ID
            title: 教案标题
            objectives: 教学目标
            content: 教案内容
            materials: 教学材料
            duration_minutes: 时长

        Returns:
            创建的教案信息
        """
        plan = LessonPlan(
            tenant_id=tenant_id,
            course_id=course_id,
            teacher_id=teacher_id,
            title=title,
            objectives=json.dumps(objectives or [], ensure_ascii=False),
            content=content,
            materials=json.dumps(materials or [], ensure_ascii=False),
            duration_minutes=duration_minutes,
            ai_generated=ai_generated,
            status="draft",
            version=1,
        )
        self.db.add(plan)
        await self.db.flush()

        return self._plan_to_dict(plan)

    async def get_lesson_plan(
        self,
        plan_id: int,
        tenant_id: int,
    ) -> Optional[Dict[str, Any]]:
        """获取教案详情"""
        stmt = select(LessonPlan).where(
            and_(
                LessonPlan.id == plan_id,
                LessonPlan.tenant_id == tenant_id,
                LessonPlan.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        plan = result.scalars().first()

        if not plan:
            return None

        return self._plan_to_dict(plan)

    async def update_lesson_plan(
        self,
        plan_id: int,
        tenant_id: int,
        teacher_id: int,
        title: Optional[str] = None,
        objectives: Optional[List[str]] = None,
        content: Optional[str] = None,
        materials: Optional[List[str]] = None,
        duration_minutes: Optional[int] = None,
        status: Optional[str] = None,
        bypass_owner_check: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """更新教案"""
        stmt = select(LessonPlan).where(
            and_(
                LessonPlan.id == plan_id,
                LessonPlan.tenant_id == tenant_id,
                LessonPlan.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        plan = result.scalars().first()

        if not plan:
            return None

        if plan.teacher_id != teacher_id and not bypass_owner_check:
            raise PermissionDeniedException(message="只能修改自己的教案")

        if title is not None:
            plan.title = title
        if objectives is not None:
            plan.objectives = json.dumps(objectives, ensure_ascii=False)
        if content is not None:
            plan.content = content
        if materials is not None:
            plan.materials = json.dumps(materials, ensure_ascii=False)
        if duration_minutes is not None:
            plan.duration_minutes = duration_minutes
        if status is not None:
            plan.status = status

        plan.version += 1
        await self.db.flush()

        return self._plan_to_dict(plan)

    async def delete_lesson_plan(
        self,
        plan_id: int,
        tenant_id: int,
        teacher_id: int,
        bypass_owner_check: bool = False,
    ) -> bool:
        """删除教案（软删除）"""
        stmt = select(LessonPlan).where(
            and_(
                LessonPlan.id == plan_id,
                LessonPlan.tenant_id == tenant_id,
                LessonPlan.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        plan = result.scalars().first()

        if not plan:
            return False

        if plan.teacher_id != teacher_id and not bypass_owner_check:
            raise PermissionDeniedException(message="只能删除自己的教案")

        plan.is_active = False
        await self.db.flush()
        return True

    async def ai_generate_lesson_plan(
        self,
        plan_id: int,
        tenant_id: int,
        teacher_id: int,
    ) -> Dict[str, Any]:
        """
        使用AI根据课程信息生成教案

        Args:
            plan_id: 教案ID
            tenant_id: 租户ID
            teacher_id: 教师ID

        Returns:
            AI生成的教案内容
        """
        plan_data = await self.get_lesson_plan(plan_id, tenant_id)
        if not plan_data:
            raise NotFoundException(message="教案不存在")

        # 调用LessonPlanAgent
        agent = LessonPlanAgent()
        result = await agent.generate_lesson_plan(
            title=plan_data["title"],
            subject="",  # 可从课程信息获取
            context={"tenant_id": tenant_id, "user_id": teacher_id},
        )

        # 更新教案内容
        generated_content = result.get("content", "")
        stmt = select(LessonPlan).where(LessonPlan.id == plan_id)
        db_result = await self.db.execute(stmt)
        plan = db_result.scalars().first()
        if plan:
            plan.content = generated_content
            plan.ai_generated = True
            plan.version += 1
            await self.db.flush()

        return {
            "id": plan_id,
            "content": generated_content,
            "ai_generated": True,
        }

    async def list_students(
        self,
        tenant_id: int,
        teacher_id: int,
        course_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取教师所教学生列表

        Args:
            tenant_id: 租户ID
            teacher_id: 教师ID
            course_id: 课程ID筛选

        Returns:
            学生列表
        """
        # 简化实现：查询该租户下的学生
        conditions = [
            User.tenant_id == tenant_id,
            User.role == "student",
            User.is_active == True,
        ]

        stmt = select(User).where(and_(*conditions)).limit(50)
        result = await self.db.execute(stmt)
        students = result.scalars().all()

        return [
            {
                "id": s.id,
                "nickname": s.nickname,
                "avatar_url": s.avatar_url,
                "grade": s.grade,
                "school": s.school,
            }
            for s in students
        ]

    async def get_learning_analytics(
        self,
        tenant_id: int,
        teacher_id: int,
        course_id: Optional[int] = None,
        time_range: str = "week",
    ) -> Dict[str, Any]:
        """
        获取学情分析数据

        Args:
            tenant_id: 租户ID
            teacher_id: 教师ID
            course_id: 课程ID
            time_range: 时间范围 day/week/month

        Returns:
            学情分析数据
        """
        # 诊断统计（简化版本）
        diagnosis_count_stmt = select(func.count(Diagnosis.id)).where(
            Diagnosis.tenant_id == tenant_id,
        )
        if course_id:
            diagnosis_count_stmt = diagnosis_count_stmt.where(
                Diagnosis.course_id == course_id,
            )
        result = await self.db.execute(diagnosis_count_stmt)
        total_diagnoses = result.scalar() or 0

        # 平均分
        avg_score_stmt = select(func.avg(Diagnosis.score)).where(
            and_(
                Diagnosis.tenant_id == tenant_id,
                Diagnosis.status == "completed",
                Diagnosis.score.isnot(None),
            ),
        )
        if course_id:
            avg_score_stmt = avg_score_stmt.where(Diagnosis.course_id == course_id)
        avg_result = await self.db.execute(avg_score_stmt)
        avg_score = avg_result.scalar() or 0.0

        detail_stmt = select(Diagnosis).where(
            and_(Diagnosis.tenant_id == tenant_id, Diagnosis.status == "completed")
        )
        if course_id:
            detail_stmt = detail_stmt.where(Diagnosis.course_id == course_id)
        diagnoses = (await self.db.execute(detail_stmt)).scalars().all()

        weakness_scores: Dict[str, List[float]] = {}
        suggestions: List[str] = []
        for diagnosis in diagnoses:
            try:
                weaknesses = json.loads(diagnosis.weaknesses or "[]")
            except (json.JSONDecodeError, TypeError):
                weaknesses = []
            if isinstance(weaknesses, dict):
                weaknesses = [weaknesses]
            for item in weaknesses if isinstance(weaknesses, list) else []:
                if isinstance(item, str):
                    weakness_scores.setdefault(item, []).append(float(diagnosis.score or 0))
                elif isinstance(item, dict):
                    name = str(item.get("name") or item.get("knowledge_point") or "").strip()
                    if name:
                        mastery = item.get("mastery", item.get("score", diagnosis.score or 0))
                        weakness_scores.setdefault(name, []).append(float(mastery or 0))
            try:
                recommendations = json.loads(diagnosis.recommendations or "[]")
            except (json.JSONDecodeError, TypeError):
                recommendations = []
            if isinstance(recommendations, str):
                recommendations = [recommendations]
            for recommendation in recommendations if isinstance(recommendations, list) else []:
                text = recommendation if isinstance(recommendation, str) else recommendation.get("description") or recommendation.get("title")
                if text and text not in suggestions:
                    suggestions.append(str(text))

        knowledge_distribution = [
            {"name": name, "mastery": round(sum(values) / len(values), 1)}
            for name, values in weakness_scores.items()
        ]
        knowledge_distribution.sort(key=lambda item: item["mastery"])

        return {
            "time_range": time_range,
            "total_diagnoses": total_diagnoses,
            "average_score": round(float(avg_score), 1),
            "student_engagement": {
                "active_students": 0,  # 后续从ClickHouse统计
                "total_students": 0,
            },
            "knowledge_distribution": knowledge_distribution,
            "weak_points": knowledge_distribution[:10],
            "suggestions": suggestions[:8],
        }

    def _plan_to_dict(self, plan: LessonPlan) -> Dict[str, Any]:
        """将LessonPlan模型转换为字典"""
        objectives = []
        if plan.objectives:
            try:
                objectives = json.loads(plan.objectives)
            except (json.JSONDecodeError, TypeError):
                pass

        materials = []
        if plan.materials:
            try:
                materials = json.loads(plan.materials)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": plan.id,
            "tenant_id": plan.tenant_id,
            "course_id": plan.course_id,
            "teacher_id": plan.teacher_id,
            "title": plan.title,
            "objectives": objectives,
            "content": plan.content,
            "materials": materials,
            "duration_minutes": plan.duration_minutes,
            "ai_generated": plan.ai_generated,
            "status": plan.status,
            "version": plan.version,
            "is_active": plan.is_active,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        }
