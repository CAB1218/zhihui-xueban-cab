"""
AI4Edu API v1 路由注册
汇总所有子路由模块
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.scenes import router as scenes_router
from app.api.v1.resources import router as resources_router
from app.api.v1.graphs import router as graphs_router
from app.api.v1.notes import router as notes_router
from app.api.v1.search import router as search_router
from app.api.v1.agents import router as agents_router
from app.api.v1.teachers import router as teachers_router
from app.api.v1.classrooms import router as classrooms_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.permissions import router as permissions_router
from app.api.v1.diagnosis import router as diagnosis_router
from app.api.v1.buddies import router as buddies_router
from app.api.v1.help import router as help_router
from app.api.v1.governance import router as governance_router
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.classroom import router as classroom_router
from app.api.v1.quota import router as quota_router
from app.api.v1.export import router as export_router
from app.api.v1.growth import router as growth_router
from app.api.v1.curriculum import router as curriculum_router
from app.api.v1.learning_analysis import router as learning_analysis_router

# v1 总路由
api_v1_router = APIRouter()

# 注册子路由
api_v1_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_v1_router.include_router(users_router, prefix="/users", tags=["用户"])
api_v1_router.include_router(scenes_router, prefix="/scenes", tags=["场景"])
api_v1_router.include_router(resources_router, prefix="/resources", tags=["资源"])
api_v1_router.include_router(graphs_router, prefix="/graphs", tags=["知识图谱"])
api_v1_router.include_router(notes_router, prefix="/notes", tags=["笔记"])
api_v1_router.include_router(search_router, prefix="/search", tags=["搜索"])
api_v1_router.include_router(agents_router, prefix="/agents", tags=["AI智能体"])
api_v1_router.include_router(teachers_router, prefix="/teachers", tags=["教师工作台"])
api_v1_router.include_router(classrooms_router, prefix="/classrooms", tags=["课堂互动"])
api_v1_router.include_router(notifications_router, prefix="/notifications", tags=["通知"])
api_v1_router.include_router(permissions_router, prefix="/permissions", tags=["权限管理"])
api_v1_router.include_router(diagnosis_router, prefix="/diagnosis", tags=["学习诊断"])
api_v1_router.include_router(buddies_router, prefix="/buddies", tags=["学伴"])
api_v1_router.include_router(help_router, prefix="/help", tags=["帮助中心"])
api_v1_router.include_router(governance_router, prefix="/governance", tags=["数据治理"])
api_v1_router.include_router(telemetry_router, tags=["遥测"])
api_v1_router.include_router(dashboard_router, tags=["仪表盘"])

# v2 新增路由
api_v1_router.include_router(classroom_router, prefix="/agents/classroom-records", tags=["课堂记录"])
api_v1_router.include_router(quota_router, prefix="/admin/quotas", tags=["配额管理"])
api_v1_router.include_router(export_router, prefix="/agents", tags=["对话导出"])
api_v1_router.include_router(growth_router, prefix="/growth", tags=["成长档案"])
api_v1_router.include_router(curriculum_router, prefix="/curriculum", tags=["课程梳理"])
api_v1_router.include_router(learning_analysis_router, prefix="/learning-analysis", tags=["学情分析"])
