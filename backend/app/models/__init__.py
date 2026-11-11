"""
AI4Edu ORM 模型包

导入所有模型确保 Base.metadata 包含所有表定义
"""
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.course import Course, CourseEnrollment  # noqa: F401
from app.models.resource import Resource, ResourceFavorite  # noqa: F401
from app.models.note import Note, NoteVersion  # noqa: F401
from app.models.scene import Scene, UserScenePreference  # noqa: F401
from app.models.notification import Notification, NotificationSetting  # noqa: F401
from app.models.agent import AgentSession, AgentMessage  # noqa: F401
from app.models.classroom import (  # noqa: F401
    Classroom, ClassroomParticipant, ClassroomPoll, ClassroomPollVote,
)
from app.models.diagnosis import Diagnosis, DiagnosisQuestion  # noqa: F401
from app.models.buddy import Buddy  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.lesson_plan import LessonPlan  # noqa: F401
from app.models.flash_card import FlashCard  # noqa: F401
from app.models.help import HelpArticle  # noqa: F401
from app.models.permission import Role, Permission, RolePermission, UserRole  # noqa: F401
from app.models.analytics import AnalyticsEvent  # noqa: F401
from app.models.teacher_method import TeacherMethod, ClassroomRecord  # noqa: F401
from app.models.usage import LLMUsageLog, TenantQuota  # noqa: F401
from app.models.export import AgentExport  # noqa: F401
from app.models.evaluation import StudentEvaluation  # noqa: F401
from app.models.curriculum import CurriculumOutline  # noqa: F401
from app.models.learning_record import LearningRecord  # noqa: F401
from app.models.course_schedule import CourseSchedule  # noqa: F401
