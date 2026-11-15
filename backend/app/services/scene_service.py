"""
智慧学伴 场景 Service
处理场景切换、推荐、配置等业务逻辑
支持基于时间规则的智能推荐
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import NotFoundException, ValidationException
from app.models.scene import Scene, UserScenePreference
from app.models.user import User
from app.schemas.scene import (
    SceneConfigResponse,
    SceneRecommendation,
    SceneSwitchRequest,
    SceneSwitchResponse,
)


# 场景默认配置
SCENE_DEFAULTS = {
    "classroom": {
        "name": "课堂模式",
        "name_en": "Classroom",
        "icon": "school",
        "primary_color": "#1976D2",
        "description": "专注课堂学习，跟随教师节奏",
    },
    "self_study": {
        "name": "自习模式",
        "name_en": "Self Study",
        "icon": "menu_book",
        "primary_color": "#388E3C",
        "description": "自主学习，按自己节奏学习",
    },
    "exam": {
        "name": "考前模式",
        "name_en": "Exam Prep",
        "icon": "quiz",
        "primary_color": "#F57C00",
        "description": "考前冲刺，集中复习备考",
    },
    "discussion": {
        "name": "讨论模式",
        "name_en": "Discussion",
        "icon": "forum",
        "primary_color": "#7B1FA2",
        "description": "小组讨论，协作学习",
    },
}

# 时间段与场景推荐规则
# 格式: (开始小时, 结束小时, 推荐场景, 原因, 置信度)
TIME_BASED_RULES = [
    (8, 9, "classroom", "早课时间，建议使用课堂模式", 0.9),
    (9, 12, "classroom", "上午课程时间，建议使用课堂模式", 0.85),
    (12, 14, "self_study", "午间自习时间，推荐自习模式", 0.7),
    (14, 17, "classroom", "下午课程时间，建议使用课堂模式", 0.85),
    (17, 19, "self_study", "课后自习时间，推荐自习模式", 0.75),
    (19, 21, "self_study", "晚间自习时间，推荐自习模式", 0.8),
    (21, 23, "exam", "晚间复习时间，推荐考前模式巩固知识", 0.65),
    (23, 24, "self_study", "深夜时段，推荐轻松的自习模式", 0.5),
    (0, 8, "self_study", "凌晨时段，建议休息或轻度学习", 0.4),
]

# 周末场景推荐
WEEKEND_RULES = [
    (8, 10, "self_study", "周末晨间，适合自主学习", 0.8),
    (10, 12, "discussion", "周末上午，适合小组讨论", 0.7),
    (12, 14, "self_study", "午间自习", 0.65),
    (14, 17, "exam", "周末下午，适合集中复习备考", 0.75),
    (17, 19, "discussion", "周末傍晚，适合交流讨论", 0.65),
    (19, 22, "self_study", "晚间自习", 0.8),
    (22, 24, "exam", "考前冲刺时间", 0.6),
    (0, 8, "self_study", "凌晨时段，建议休息", 0.4),
]


class SceneService:
    """场景服务"""

    VALID_SCENE_TYPES = {"classroom", "self_study", "exam", "discussion"}

    def __init__(self, db: AsyncSession = None):
        """初始化场景服务"""
        self.db = db

    async def switch_scene(self, user_id: int, request: SceneSwitchRequest) -> SceneSwitchResponse:
        """
        切换场景

        Args:
            user_id: 用户ID
            request: 场景切换请求

        Returns:
            SceneSwitchResponse: 切换后的场景配置

        Raises:
            ValidationException: 无效的场景类型
        """
        if request.scene_type not in self.VALID_SCENE_TYPES:
            raise ValidationException(message=f"无效的场景类型: {request.scene_type}")

        # 获取场景完整配置
        scene_config = await self._get_scene_from_db(request.scene_type)

        if self.db:
            # 更新用户场景偏好
            result = await self.db.execute(
                select(UserScenePreference).where(
                    UserScenePreference.user_id == user_id,
                    UserScenePreference.is_current == True,
                )
            )
            current_pref = result.scalars().first()

            if current_pref:
                current_pref.is_current = False

            # 创建或更新新偏好
            new_pref_result = await self.db.execute(
                select(UserScenePreference).where(
                    UserScenePreference.user_id == user_id,
                    UserScenePreference.scene_type == request.scene_type,
                )
            )
            new_pref = new_pref_result.scalars().first()

            if new_pref:
                new_pref.is_current = True
                new_pref.last_accessed_at = datetime.utcnow()
            else:
                new_pref = UserScenePreference(
                    user_id=user_id,
                    scene_type=request.scene_type,
                    is_current=True,
                    last_accessed_at=datetime.utcnow(),
                )
                self.db.add(new_pref)

            await self.db.commit()

        # 构建响应
        layout_config = None
        feature_flags = None
        widgets = None

        if scene_config:
            if scene_config.layout_config:
                try:
                    layout_config = json.loads(scene_config.layout_config)
                except (json.JSONDecodeError, TypeError):
                    pass
            if scene_config.feature_flags:
                try:
                    feature_flags = json.loads(scene_config.feature_flags)
                except (json.JSONDecodeError, TypeError):
                    pass
            if scene_config.default_widgets:
                try:
                    widgets = json.loads(scene_config.default_widgets)
                except (json.JSONDecodeError, TypeError):
                    pass

        defaults = SCENE_DEFAULTS.get(request.scene_type, {})
        return SceneSwitchResponse(
            scene_type=request.scene_type,
            scene_name=scene_config.name if scene_config else defaults.get("name", ""),
            primary_color=scene_config.primary_color if scene_config else defaults.get("primary_color", "#000000"),
            layout_config=layout_config,
            feature_flags=feature_flags,
            widgets=widgets,
        )

    async def get_current_scene(self, user_id: int) -> SceneConfigResponse:
        """
        获取用户当前场景

        Args:
            user_id: 用户ID

        Returns:
            SceneConfigResponse: 场景配置
        """
        if self.db:
            # 从数据库查询用户当前场景偏好
            result = await self.db.execute(
                select(UserScenePreference).where(
                    UserScenePreference.user_id == user_id,
                    UserScenePreference.is_current == True,
                )
            )
            pref = result.scalars().first()

            if pref:
                return await self.get_scene_config(pref.scene_type)

        # 默认返回课堂模式
        return await self.get_scene_config("classroom")

    async def get_recommendation(self, user_id: int, context: Optional[str] = None) -> SceneRecommendation:
        """
        获取场景推荐（基于时间规则 + 用户行为）

        Args:
            user_id: 用户ID
            context: 上下文信息

        Returns:
            SceneRecommendation: 场景推荐结果
        """
        now = datetime.utcnow()
        # 转换为中国时区
        china_tz = timezone(timedelta(hours=8))
        local_now = now.astimezone(china_tz)
        hour = local_now.hour
        is_weekend = local_now.weekday() >= 5  # 5=周六, 6=周日

        # 根据时间规则推荐
        rules = WEEKEND_RULES if is_weekend else TIME_BASED_RULES
        time_context = self._get_time_context(local_now)

        recommended_scene = "classroom"
        reason = "当前为上课时间，建议切换到课堂模式"
        confidence = 0.8

        for start_h, end_h, scene, rsn, conf in rules:
            if start_h <= hour < end_h:
                recommended_scene = scene
                reason = rsn
                confidence = conf
                break

        # 如果有用户偏好数据，提高置信度
        if self.db:
            pref_result = await self.db.execute(
                select(UserScenePreference).where(
                    UserScenePreference.user_id == user_id,
                    UserScenePreference.scene_type == recommended_scene,
                )
            )
            if pref_result.scalars().first():
                confidence = min(confidence + 0.1, 1.0)

        # 构建备选场景
        all_scenes = list(self.VALID_SCENE_TYPES)
        alternative_scenes = [s for s in all_scenes if s != recommended_scene][:2]

        return SceneRecommendation(
            recommended_scene=recommended_scene,
            reason=reason,
            confidence=confidence,
            alternative_scenes=alternative_scenes,
            time_context=time_context,
        )

    async def get_scene_config(self, scene_type: str) -> SceneConfigResponse:
        """
        获取场景配置

        Args:
            scene_type: 场景类型

        Returns:
            SceneConfigResponse: 场景配置

        Raises:
            NotFoundException: 场景不存在
        """
        scene = await self._get_scene_from_db(scene_type)

        if scene:
            layout_config = None
            feature_flags = None
            default_widgets = None

            if scene.layout_config:
                try:
                    layout_config = json.loads(scene.layout_config)
                except (json.JSONDecodeError, TypeError):
                    pass
            if scene.feature_flags:
                try:
                    feature_flags = json.loads(scene.feature_flags)
                except (json.JSONDecodeError, TypeError):
                    pass
            if scene.default_widgets:
                try:
                    default_widgets = json.loads(scene.default_widgets)
                except (json.JSONDecodeError, TypeError):
                    pass

            return SceneConfigResponse(
                scene_type=scene.scene_type,
                name=scene.name,
                name_en=scene.name_en,
                icon=scene.icon,
                primary_color=scene.primary_color,
                description=scene.description,
                layout_config=layout_config,
                feature_flags=feature_flags,
                default_widgets=default_widgets,
                ai_prompt_template=scene.ai_prompt_template,
            )

        # 回退到默认配置
        if scene_type not in SCENE_DEFAULTS:
            raise NotFoundException(message=f"场景不存在: {scene_type}")

        defaults = SCENE_DEFAULTS[scene_type]
        return SceneConfigResponse(
            scene_type=scene_type,
            name=defaults["name"],
            name_en=defaults["name_en"],
            icon=defaults["icon"],
            primary_color=defaults["primary_color"],
            description=defaults.get("description"),
        )

    async def list_scenes(self) -> list[SceneConfigResponse]:
        """
        获取所有可用场景

        Returns:
            list[SceneConfigResponse]: 场景列表
        """
        scenes = []
        if self.db:
            result = await self.db.execute(
                select(Scene).where(Scene.is_active == True).order_by(Scene.sort_order)
            )
            db_scenes = result.scalars().all()

            for scene in db_scenes:
                layout_config = None
                feature_flags = None
                default_widgets = None

                if scene.layout_config:
                    try:
                        layout_config = json.loads(scene.layout_config)
                    except (json.JSONDecodeError, TypeError):
                        pass
                if scene.feature_flags:
                    try:
                        feature_flags = json.loads(scene.feature_flags)
                    except (json.JSONDecodeError, TypeError):
                        pass
                if scene.default_widgets:
                    try:
                        default_widgets = json.loads(scene.default_widgets)
                    except (json.JSONDecodeError, TypeError):
                        pass

                scenes.append(SceneConfigResponse(
                    scene_type=scene.scene_type,
                    name=scene.name,
                    name_en=scene.name_en,
                    icon=scene.icon,
                    primary_color=scene.primary_color,
                    description=scene.description,
                    layout_config=layout_config,
                    feature_flags=feature_flags,
                    default_widgets=default_widgets,
                    ai_prompt_template=scene.ai_prompt_template,
                ))

        if not scenes:
            # 回退到默认
            for scene_type, defaults in SCENE_DEFAULTS.items():
                scenes.append(SceneConfigResponse(
                    scene_type=scene_type,
                    name=defaults["name"],
                    name_en=defaults["name_en"],
                    icon=defaults["icon"],
                    primary_color=defaults["primary_color"],
                    description=defaults.get("description"),
                ))

        return scenes

    def _get_time_context(self, local_now: datetime) -> str:
        """获取时间上下文描述"""
        hour = local_now.hour
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[local_now.weekday()]

        if 6 <= hour < 9:
            period = "早晨"
        elif 9 <= hour < 12:
            period = "上午"
        elif 12 <= hour < 14:
            period = "午间"
        elif 14 <= hour < 17:
            period = "下午"
        elif 17 <= hour < 19:
            period = "傍晚"
        elif 19 <= hour < 22:
            period = "晚间"
        else:
            period = "深夜"

        return f"{weekday} {period} ({hour}:00)"

    async def _get_scene_from_db(self, scene_type: str) -> Optional[Scene]:
        """从数据库查询场景"""
        if not self.db:
            return None

        result = await self.db.execute(
            select(Scene).where(Scene.scene_type == scene_type, Scene.is_active == True)
        )
        return result.scalars().first()
