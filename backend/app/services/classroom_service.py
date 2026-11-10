"""
AI4Edu 课堂服务
创建/加入/离开课堂、举手、投票、弹幕、统计
"""
import json
import logging
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, PermissionDeniedException, ValidationException
from app.models.classroom import Classroom, ClassroomParticipant, ClassroomPoll, ClassroomPollVote
from app.schemas.common import PaginationParams

logger = logging.getLogger(__name__)


class ClassroomService:
    """课堂服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_classroom(
        self,
        tenant_id: int,
        teacher_id: int,
        course_id: int,
        title: str,
        description: Optional[str] = None,
        max_participants: int = 100,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建课堂

        Args:
            tenant_id: 租户ID
            teacher_id: 教师ID
            course_id: 课程ID
            title: 课堂主题
            description: 课堂描述
            max_participants: 最大参与人数
            settings: 课堂配置

        Returns:
            创建的课堂信息
        """
        # 生成加入码
        access_code = self._generate_access_code()

        classroom = Classroom(
            tenant_id=tenant_id,
            course_id=course_id,
            teacher_id=teacher_id,
            title=title,
            description=description,
            status="active",
            access_code=access_code,
            max_participants=max_participants,
            participant_count=1,
            started_at=datetime.utcnow(),
            settings=json.dumps(settings or {}, ensure_ascii=False),
        )
        self.db.add(classroom)
        await self.db.flush()

        # 创建者（教师）自动加入课堂，否则举手/投票等操作会报「未在该课堂中」
        self.db.add(
            ClassroomParticipant(
                classroom_id=classroom.id,
                user_id=teacher_id,
                role="teacher",
                hand_raised=False,
            )
        )
        await self.db.flush()

        return self._classroom_to_dict(classroom)

    async def get_classroom(
        self,
        classroom_id: int,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取课堂详情

        Args:
            classroom_id: 课堂ID
            tenant_id: 租户ID

        Returns:
            课堂信息
        """
        conditions = [Classroom.id == classroom_id]
        # 自助注册的用户 tenant_id 可能为空，此时不做租户隔离（开发/演示环境）
        if tenant_id:
            conditions.append(Classroom.tenant_id == tenant_id)
        stmt = select(Classroom).where(and_(*conditions))
        result = await self.db.execute(stmt)
        classroom = result.scalars().first()

        if not classroom:
            return None

        return self._classroom_to_dict(classroom)

    async def join_classroom(
        self,
        classroom_id: int,
        tenant_id: Optional[int],
        user_id: int,
        access_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        加入课堂

        Args:
            classroom_id: 课堂ID
            tenant_id: 租户ID
            user_id: 用户ID
            access_code: 加入码

        Returns:
            加入结果
        """
        conditions = [Classroom.id == classroom_id]
        if tenant_id:
            conditions.append(Classroom.tenant_id == tenant_id)
        stmt = select(Classroom).where(and_(*conditions))
        result = await self.db.execute(stmt)
        classroom = result.scalars().first()

        if not classroom:
            raise NotFoundException(message="课堂不存在")

        if classroom.status == "ended":
            raise ValidationException(message="课堂已结束")

        # 验证加入码（如果有）
        if classroom.access_code and access_code and classroom.access_code != access_code:
            raise ValidationException(message="加入码错误")

        # 检查是否已加入
        existing = await self._get_participant(classroom_id, user_id)
        if existing and existing.left_at is None:
            raise ValidationException(message="已在该课堂中")

        # 检查人数上限
        if classroom.participant_count >= classroom.max_participants:
            raise ValidationException(message="课堂人数已满")

        # 加入课堂
        participant = ClassroomParticipant(
            classroom_id=classroom_id,
            user_id=user_id,
            role="student",
            hand_raised=False,
        )
        self.db.add(participant)

        # 更新参与人数
        classroom.participant_count += 1

        # 如果课堂还是scheduled状态，激活
        if classroom.status == "scheduled":
            classroom.status = "active"
            classroom.started_at = datetime.utcnow()

        await self.db.flush()

        return {
            "classroom_id": classroom_id,
            "user_id": user_id,
            "role": "student",
            "status": classroom.status,
        }

    async def leave_classroom(
        self,
        classroom_id: int,
        tenant_id: int,
        user_id: int,
    ) -> bool:
        """
        离开课堂

        Args:
            classroom_id: 课堂ID
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            是否离开成功
        """
        participant = await self._get_participant(classroom_id, user_id)
        if not participant or participant.left_at is not None:
            return False

        participant.left_at = datetime.utcnow()

        # 更新参与人数
        stmt = select(Classroom).where(Classroom.id == classroom_id)
        result = await self.db.execute(stmt)
        classroom = result.scalars().first()
        if classroom:
            classroom.participant_count = max(0, classroom.participant_count - 1)

        await self.db.flush()
        return True

    async def raise_hand(
        self,
        classroom_id: int,
        user_id: int,
        raised: bool = True,
    ) -> bool:
        """
        举手/放下

        Args:
            classroom_id: 课堂ID
            user_id: 用户ID
            raised: True=举手，False=放下

        Returns:
            是否操作成功
        """
        participant = await self._get_participant(classroom_id, user_id)
        if not participant:
            raise NotFoundException(message="未在该课堂中")

        participant.hand_raised = raised
        await self.db.flush()
        return True

    async def create_poll(
        self,
        classroom_id: int,
        teacher_id: int,
        question: str,
        options: List[str],
        poll_type: str = "single",
        is_anonymous: bool = False,
        bypass_owner_check: bool = False,
    ) -> Dict[str, Any]:
        """
        发起课堂投票

        Args:
            classroom_id: 课堂ID
            teacher_id: 教师ID
            question: 投票问题
            options: 选项列表
            poll_type: 类型 single/multiple
            is_anonymous: 是否匿名

        Returns:
            投票信息
        """
        # 验证教师身份
        stmt = select(Classroom).where(Classroom.id == classroom_id)
        result = await self.db.execute(stmt)
        classroom = result.scalars().first()

        if not classroom:
            raise NotFoundException(message="课堂不存在")

        if classroom.teacher_id != teacher_id and not bypass_owner_check:
            raise PermissionDeniedException(message="只有教师可以发起投票")

        poll = ClassroomPoll(
            classroom_id=classroom_id,
            question=question,
            options=json.dumps(options, ensure_ascii=False),
            poll_type=poll_type,
            is_anonymous=is_anonymous,
            status="active",
            created_by=teacher_id,
        )
        self.db.add(poll)
        await self.db.flush()

        return {
            "id": poll.id,
            "classroom_id": classroom_id,
            "question": question,
            "options": options,
            "poll_type": poll_type,
            "is_anonymous": is_anonymous,
            "status": "active",
            "is_active": True,
            "total_votes": 0,
            "created_at": poll.created_at.isoformat() if poll.created_at else None,
        }

    async def vote_poll(
        self,
        poll_id: int,
        user_id: int,
        selected_options: List[int],
    ) -> bool:
        """
        对投票进行投票

        Args:
            poll_id: 投票ID
            user_id: 用户ID
            selected_options: 选中的选项索引列表

        Returns:
            是否投票成功
        """
        stmt = select(ClassroomPoll).where(ClassroomPoll.id == poll_id)
        result = await self.db.execute(stmt)
        poll = result.scalars().first()

        if not poll:
            raise NotFoundException(message="投票不存在")

        if poll.status != "active":
            raise ValidationException(message="投票已关闭")

        # 检查是否已投票
        existing_stmt = select(ClassroomPollVote).where(
            and_(
                ClassroomPollVote.poll_id == poll_id,
                ClassroomPollVote.user_id == user_id,
            )
        )
        existing_result = await self.db.execute(existing_stmt)
        if existing_result.scalars().first():
            raise ValidationException(message="已投过票")

        vote = ClassroomPollVote(
            poll_id=poll_id,
            user_id=user_id,
            selected_options=json.dumps(selected_options, ensure_ascii=False),
        )
        self.db.add(vote)
        await self.db.flush()
        return True

    async def get_poll_result(
        self,
        poll_id: int,
        tenant_id: int,
    ) -> Dict[str, Any]:
        """
        获取投票结果

        Args:
            poll_id: 投票ID
            tenant_id: 租户ID

        Returns:
            投票结果统计
        """
        stmt = select(ClassroomPoll).where(ClassroomPoll.id == poll_id)
        result = await self.db.execute(stmt)
        poll = result.scalars().first()

        if not poll:
            raise NotFoundException(message="投票不存在")

        # 获取所有投票记录
        votes_stmt = select(ClassroomPollVote).where(ClassroomPollVote.poll_id == poll_id)
        votes_result = await self.db.execute(votes_stmt)
        votes = votes_result.scalars().all()

        # 统计结果
        options = json.loads(poll.options) if poll.options else []
        option_counts: Dict[int, int] = {i: 0 for i in range(len(options))}

        for vote in votes:
            selected = json.loads(vote.selected_options) if vote.selected_options else []
            for idx in selected:
                if idx in option_counts:
                    option_counts[idx] += 1

        total_votes = len(votes)
        results = []
        for i, option_text in enumerate(options):
            count = option_counts.get(i, 0)
            results.append({
                "index": i,
                "text": option_text,
                "count": count,
                "percentage": round(count / max(total_votes, 1) * 100, 1),
            })

        return {
            "id": poll.id,
            "question": poll.question,
            "options": options,
            "poll_type": poll.poll_type,
            "is_anonymous": poll.is_anonymous,
            "status": poll.status,
            "total_votes": total_votes,
            "results": results,
            "created_at": poll.created_at.isoformat() if poll.created_at else None,
            "closed_at": poll.closed_at.isoformat() if poll.closed_at else None,
        }

    async def list_classrooms(
        self,
        tenant_id: int,
        user_id: int,
        role: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        获取「我的课堂」列表

        教师返回自己创建的课堂，学生返回已加入的课堂，管理员返回租户内全部课堂。
        """
        if role in ("admin", "super_admin"):
            stmt = select(Classroom).where(Classroom.tenant_id == tenant_id)
        elif role == "teacher":
            stmt = select(Classroom).where(
                and_(Classroom.tenant_id == tenant_id, Classroom.teacher_id == user_id)
            )
        else:
            stmt = (
                select(Classroom)
                .join(ClassroomParticipant, ClassroomParticipant.classroom_id == Classroom.id)
                .where(
                    and_(
                        ClassroomParticipant.user_id == user_id,
                        ClassroomParticipant.left_at.is_(None),
                    )
                )
            )

        stmt = stmt.order_by(desc(Classroom.id)).limit(limit)
        result = await self.db.execute(stmt)
        return [self._classroom_to_dict(item) for item in result.scalars().all()]

    async def list_participants(self, classroom_id: int) -> List[Dict[str, Any]]:
        """获取课堂参与者列表（不含已离开）"""
        from app.models.user import User

        stmt = (
            select(ClassroomParticipant, User)
            .join(User, User.id == ClassroomParticipant.user_id)
            .where(
                and_(
                    ClassroomParticipant.classroom_id == classroom_id,
                    ClassroomParticipant.left_at.is_(None),
                )
            )
            .order_by(ClassroomParticipant.role.desc(), ClassroomParticipant.id.asc())
        )
        result = await self.db.execute(stmt)

        participants: List[Dict[str, Any]] = []
        for participant, user in result.all():
            participants.append(
                {
                    "user_id": participant.user_id,
                    "name": user.nickname or user.email,
                    "avatar_url": user.avatar_url,
                    "role": participant.role,
                    "hand_raised": bool(participant.hand_raised),
                    "is_online": True,
                    "joined_at": participant.joined_at.isoformat() if participant.joined_at else None,
                }
            )
        return participants

    async def list_polls(self, classroom_id: int) -> List[Dict[str, Any]]:
        """获取课堂投票列表（含票数）"""
        stmt = (
            select(ClassroomPoll)
            .where(ClassroomPoll.classroom_id == classroom_id)
            .order_by(desc(ClassroomPoll.id))
        )
        result = await self.db.execute(stmt)
        polls = result.scalars().all()

        counts: Dict[int, int] = {}
        if polls:
            count_stmt = (
                select(ClassroomPollVote.poll_id, func.count(ClassroomPollVote.id))
                .where(ClassroomPollVote.poll_id.in_([p.id for p in polls]))
                .group_by(ClassroomPollVote.poll_id)
            )
            count_result = await self.db.execute(count_stmt)
            counts = {row[0]: row[1] for row in count_result.all()}

        items: List[Dict[str, Any]] = []
        for poll in polls:
            try:
                options = json.loads(poll.options) if isinstance(poll.options, str) else poll.options
            except (json.JSONDecodeError, TypeError):
                options = []
            items.append(
                {
                    "id": poll.id,
                    "classroom_id": poll.classroom_id,
                    "question": poll.question,
                    "options": options,
                    "poll_type": poll.poll_type,
                    "is_anonymous": bool(poll.is_anonymous),
                    "status": poll.status,
                    "is_active": poll.status == "active",
                    "total_votes": counts.get(poll.id, 0),
                    "created_at": poll.created_at.isoformat() if poll.created_at else None,
                }
            )
        return items

    async def join_by_code(
        self,
        access_code: str,
        tenant_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """通过加入码加入课堂"""
        stmt = select(Classroom).where(Classroom.access_code == access_code)
        result = await self.db.execute(stmt)
        classroom = result.scalars().first()

        if not classroom:
            raise NotFoundException(message="加入码无效")

        await self.join_classroom(
            classroom_id=classroom.id,
            tenant_id=tenant_id,
            user_id=user_id,
            access_code=access_code,
        )
        return self._classroom_to_dict(classroom)

    async def end_classroom(
        self,
        classroom_id: int,
        teacher_id: int,
        bypass_owner_check: bool = False,
    ) -> bool:
        """
        结束课堂

        Args:
            classroom_id: 课堂ID
            teacher_id: 教师ID

        Returns:
            是否结束成功
        """
        stmt = select(Classroom).where(Classroom.id == classroom_id)
        result = await self.db.execute(stmt)
        classroom = result.scalars().first()

        if not classroom:
            raise NotFoundException(message="课堂不存在")

        if classroom.teacher_id != teacher_id and not bypass_owner_check:
            raise PermissionDeniedException(message="只有教师可以结束课堂")

        classroom.status = "ended"
        classroom.ended_at = datetime.utcnow()
        await self.db.flush()
        return True

    async def _get_participant(
        self,
        classroom_id: int,
        user_id: int,
    ) -> Optional[ClassroomParticipant]:
        """获取课堂参与者"""
        stmt = select(ClassroomParticipant).where(
            and_(
                ClassroomParticipant.classroom_id == classroom_id,
                ClassroomParticipant.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    def _generate_access_code(self) -> str:
        """生成6位加入码"""
        return "".join(random.choices(string.digits, k=6))

    def _classroom_to_dict(self, classroom: Classroom) -> Dict[str, Any]:
        """将Classroom模型转换为字典"""
        settings_data = {}
        if classroom.settings:
            try:
                settings_data = json.loads(classroom.settings)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": classroom.id,
            "tenant_id": classroom.tenant_id,
            "course_id": classroom.course_id,
            "teacher_id": classroom.teacher_id,
            "title": classroom.title,
            "description": classroom.description,
            "status": classroom.status,
            "access_code": classroom.access_code,
            "max_participants": classroom.max_participants,
            "participant_count": classroom.participant_count,
            "settings": settings_data,
            "started_at": classroom.started_at.isoformat() if classroom.started_at else None,
            "ended_at": classroom.ended_at.isoformat() if classroom.ended_at else None,
            "created_at": classroom.created_at.isoformat() if classroom.created_at else None,
        }
