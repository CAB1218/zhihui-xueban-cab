"""
智慧学伴 诊断服务
创建诊断、答题、IRT计算、生成报告、推荐学习路径
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.diagnosis_agent import DiagnosisAgent, IRT_PARAMS, estimate_theta_mle
from app.core.exceptions import NotFoundException, ValidationException
from app.models.diagnosis import Diagnosis, DiagnosisQuestion
from app.models.flash_card import FlashCard
from app.schemas.common import PaginationParams

logger = logging.getLogger(__name__)


class DiagnosisService:
    """诊断服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def start_diagnosis(
        self,
        tenant_id: int,
        user_id: int,
        diagnosis_type: str = "knowledge",
        title: str = "知识诊断",
        course_id: Optional[int] = None,
        subject: Optional[str] = None,
        knowledge_points: Optional[List[str]] = None,
        question_count: int = 10,
    ) -> Dict[str, Any]:
        """
        启动诊断评估

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            diagnosis_type: 诊断类型
            title: 诊断标题
            course_id: 课程ID
            subject: 学科
            knowledge_points: 知识点范围
            question_count: 题目数量

        Returns:
            诊断信息（含题目列表）
        """
        # 创建诊断记录
        diagnosis = Diagnosis(
            tenant_id=tenant_id,
            user_id=user_id,
            course_id=course_id,
            diagnosis_type=diagnosis_type,
            title=title,
            status="pending",
            total_questions=0,
            correct_count=0,
        )
        self.db.add(diagnosis)
        await self.db.flush()

        # 使用QuizAgent生成诊断题目
        questions = await self._generate_diagnosis_questions(
            diagnosis_id=diagnosis.id,
            subject=subject or "数学",
            knowledge_points=knowledge_points,
            question_count=question_count,
        )

        # 保存题目到数据库
        for i, q in enumerate(questions):
            dq = DiagnosisQuestion(
                diagnosis_id=diagnosis.id,
                question_text=q.get("question_text", ""),
                question_type=q.get("question_type", "choice"),
                options=json.dumps(q.get("options", {}), ensure_ascii=False) if q.get("options") else None,
                correct_answer=q.get("correct_answer", ""),
                knowledge_points=json.dumps(q.get("knowledge_points", []), ensure_ascii=False),
                difficulty=q.get("difficulty", "medium"),
                sort_order=i,
            )
            self.db.add(dq)

        diagnosis.total_questions = len(questions)
        diagnosis.status = "in_progress"
        diagnosis.started_at = datetime.utcnow()
        await self.db.flush()

        # 返回不含正确答案的题目列表
        question_list = []
        stmt = (
            select(DiagnosisQuestion)
            .where(DiagnosisQuestion.diagnosis_id == diagnosis.id)
            .order_by(DiagnosisQuestion.sort_order)
        )
        result = await self.db.execute(stmt)
        db_questions = result.scalars().all()

        for q in db_questions:
            options_data = None
            if q.options:
                try:
                    options_data = json.loads(q.options)
                except (json.JSONDecodeError, TypeError):
                    options_data = None

            question_list.append({
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": options_data,
                "difficulty": q.difficulty,
                "sort_order": q.sort_order,
            })

        return {
            "id": diagnosis.id,
            "tenant_id": diagnosis.tenant_id,
            "user_id": diagnosis.user_id,
            "diagnosis_type": diagnosis.diagnosis_type,
            "title": diagnosis.title,
            "status": diagnosis.status,
            "total_questions": diagnosis.total_questions,
            "started_at": diagnosis.started_at.isoformat() if diagnosis.started_at else None,
            "questions": question_list,
        }

    async def submit_answers(
        self,
        diagnosis_id: int,
        tenant_id: int,
        user_id: int,
        answers: Dict[str, str],
        duration_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        提交诊断答案

        Args:
            diagnosis_id: 诊断ID
            tenant_id: 租户ID
            user_id: 用户ID
            answers: 答案映射 {question_id: user_answer}
            duration_seconds: 用时

        Returns:
            诊断结果
        """
        # 获取诊断记录
        stmt = select(Diagnosis).where(
            and_(
                Diagnosis.id == diagnosis_id,
                Diagnosis.tenant_id == tenant_id,
                Diagnosis.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        diagnosis = result.scalars().first()

        if not diagnosis:
            raise NotFoundException(message="诊断不存在")

        if diagnosis.status != "in_progress":
            raise ValidationException(message="诊断不在进行中")

        # 获取题目
        q_stmt = select(DiagnosisQuestion).where(
            DiagnosisQuestion.diagnosis_id == diagnosis_id
        )
        q_result = await self.db.execute(q_stmt)
        questions = q_result.scalars().all()

        # 批改
        correct_count = 0
        irt_responses: List[Dict[str, Any]] = []
        knowledge_stats: Dict[str, Dict[str, int]] = {}

        for q in questions:
            q_id = str(q.id)
            user_answer = answers.get(q_id, "")
            is_correct = user_answer.strip().lower() == q.correct_answer.strip().lower()

            q.user_answer = user_answer
            q.is_correct = is_correct

            if is_correct:
                correct_count += 1

            # IRT数据
            irt_param = IRT_PARAMS.get(q.difficulty, IRT_PARAMS["medium"])
            irt_responses.append({
                "is_correct": is_correct,
                "difficulty": q.difficulty,
                "difficulty_b": irt_param["b"],
                "discrimination": irt_param["a"],
                "guessing": 0.25 if q.question_type == "choice" else 0.0,
            })

            # 知识点统计
            kp_list = []
            if q.knowledge_points:
                try:
                    kp_list = json.loads(q.knowledge_points)
                except (json.JSONDecodeError, TypeError):
                    kp_list = [q.knowledge_points]

            for kp in kp_list:
                if kp not in knowledge_stats:
                    knowledge_stats[kp] = {"total": 0, "correct": 0}
                knowledge_stats[kp]["total"] += 1
                if is_correct:
                    knowledge_stats[kp]["correct"] += 1

        # IRT能力估算
        theta = estimate_theta_mle(irt_responses)

        # 更新诊断记录
        diagnosis.correct_count = correct_count
        diagnosis.score = round(correct_count / max(len(questions), 1) * 100, 1)
        diagnosis.duration_seconds = duration_seconds
        diagnosis.status = "completed"
        diagnosis.completed_at = datetime.utcnow()
        diagnosis.weaknesses = json.dumps(
            [kp for kp, s in knowledge_stats.items() if s["correct"] / max(s["total"], 1) < 0.6],
            ensure_ascii=False,
        )
        diagnosis.strengths = json.dumps(
            [kp for kp, s in knowledge_stats.items() if s["correct"] / max(s["total"], 1) >= 0.8],
            ensure_ascii=False,
        )

        await self.db.flush()

        return {
            "id": diagnosis.id,
            "status": "completed",
            "score": diagnosis.score,
            "correct_count": correct_count,
            "total_questions": diagnosis.total_questions,
            "theta": round(theta, 3),
            "duration_seconds": duration_seconds,
        }

    async def get_diagnosis(
        self,
        diagnosis_id: int,
        tenant_id: int,
    ) -> Optional[Dict[str, Any]]:
        """获取诊断详情"""
        stmt = select(Diagnosis).where(
            and_(
                Diagnosis.id == diagnosis_id,
                Diagnosis.tenant_id == tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        diagnosis = result.scalars().first()

        if not diagnosis:
            return None

        return self._diagnosis_to_dict(diagnosis)

    async def get_report(
        self,
        diagnosis_id: int,
        tenant_id: int,
    ) -> Dict[str, Any]:
        """
        获取诊断报告

        Args:
            diagnosis_id: 诊断ID
            tenant_id: 租户ID

        Returns:
            诊断报告
        """
        diagnosis_data = await self.get_diagnosis(diagnosis_id, tenant_id)
        if not diagnosis_data:
            raise NotFoundException(message="诊断不存在")

        if diagnosis_data["status"] != "completed":
            raise ValidationException(message="诊断尚未完成")

        # 使用DiagnosisAgent生成报告
        agent = DiagnosisAgent()
        report = await agent.generate_diagnosis_report(diagnosis_data)

        return report

    async def get_weaknesses(
        self,
        diagnosis_id: int,
        tenant_id: int,
    ) -> List[str]:
        """获取知识弱点"""
        stmt = select(Diagnosis).where(
            and_(Diagnosis.id == diagnosis_id, Diagnosis.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        diagnosis = result.scalars().first()

        if not diagnosis:
            raise NotFoundException(message="诊断不存在")

        weaknesses = []
        if diagnosis.weaknesses:
            try:
                weaknesses = json.loads(diagnosis.weaknesses)
            except (json.JSONDecodeError, TypeError):
                pass

        return weaknesses

    async def generate_review_cards(
        self,
        diagnosis_id: int,
        tenant_id: int,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """
        基于诊断结果生成复习卡片

        Args:
            diagnosis_id: 诊断ID
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            生成的复习卡片列表
        """
        diagnosis_data = await self.get_diagnosis(diagnosis_id, tenant_id)
        if not diagnosis_data:
            raise NotFoundException(message="诊断不存在")

        # 获取答错的题目
        stmt = select(DiagnosisQuestion).where(
            and_(
                DiagnosisQuestion.diagnosis_id == diagnosis_id,
                DiagnosisQuestion.is_correct == False,
            )
        )
        result = await self.db.execute(stmt)
        wrong_questions = result.scalars().all()

        cards: List[Dict[str, Any]] = []
        for q in wrong_questions:
            # 创建复习卡片
            card = FlashCard(
                tenant_id=tenant_id,
                user_id=user_id,
                diagnosis_id=diagnosis_id,
                front=q.question_text,
                back=q.correct_answer,
                card_type="basic",
                knowledge_point=json.loads(q.knowledge_points)[0] if q.knowledge_points else None,
                difficulty=q.difficulty,
                ai_generated=True,
            )
            self.db.add(card)
            cards.append({
                "front": q.question_text,
                "back": q.correct_answer,
                "knowledge_point": json.loads(q.knowledge_points)[0] if q.knowledge_points else None,
                "difficulty": q.difficulty,
            })

        await self.db.flush()
        return cards

    async def get_history(
        self,
        tenant_id: int,
        user_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """获取诊断历史"""
        stmt = (
            select(Diagnosis)
            .where(
                and_(
                    Diagnosis.tenant_id == tenant_id,
                    Diagnosis.user_id == user_id,
                )
            )
            .order_by(desc(Diagnosis.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        diagnoses = result.scalars().all()

        return [self._diagnosis_to_dict(d) for d in diagnoses]

    async def _generate_diagnosis_questions(
        self,
        diagnosis_id: int,
        subject: str,
        knowledge_points: Optional[List[str]],
        question_count: int,
    ) -> List[Dict[str, Any]]:
        """生成诊断题目"""
        from app.agents.quiz_agent import QuizAgent

        quiz_agent = QuizAgent()
        result = await quiz_agent.generate_quiz(
            subject=subject,
            knowledge_points=knowledge_points,
            question_type="choice",
            difficulty="medium",
            count=question_count,
        )
        return result.get("questions", [])

    def _diagnosis_to_dict(self, diagnosis: Diagnosis) -> Dict[str, Any]:
        """将Diagnosis模型转换为字典"""
        weaknesses = []
        if diagnosis.weaknesses:
            try:
                weaknesses = json.loads(diagnosis.weaknesses)
            except (json.JSONDecodeError, TypeError):
                pass

        strengths = []
        if diagnosis.strengths:
            try:
                strengths = json.loads(diagnosis.strengths)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": diagnosis.id,
            "tenant_id": diagnosis.tenant_id,
            "user_id": diagnosis.user_id,
            "course_id": diagnosis.course_id,
            "diagnosis_type": diagnosis.diagnosis_type,
            "title": diagnosis.title,
            "status": diagnosis.status,
            "total_questions": diagnosis.total_questions,
            "correct_count": diagnosis.correct_count,
            "score": diagnosis.score,
            "duration_seconds": diagnosis.duration_seconds,
            "weaknesses": weaknesses,
            "strengths": strengths,
            "started_at": diagnosis.started_at.isoformat() if diagnosis.started_at else None,
            "completed_at": diagnosis.completed_at.isoformat() if diagnosis.completed_at else None,
            "created_at": diagnosis.created_at.isoformat() if diagnosis.created_at else None,
        }
