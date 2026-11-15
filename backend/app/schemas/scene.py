"""
智慧学伴 场景 Schema
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SceneSwitchRequest(BaseModel):
    """场景切换请求"""

    scene_type: str = Field(..., description="目标场景类型: classroom/self_study/exam/discussion")
    course_id: Optional[int] = Field(default=None, description="关联课程ID（可选）")


class SceneSwitchResponse(BaseModel):
    """场景切换响应"""

    scene_type: str = Field(..., description="当前场景类型")
    scene_name: str = Field(..., description="场景名称")
    primary_color: str = Field(..., description="主题色")
    layout_config: Optional[Dict[str, Any]] = Field(default=None, description="布局配置")
    feature_flags: Optional[Dict[str, bool]] = Field(default=None, description="功能开关")
    widgets: Optional[List[str]] = Field(default=None, description="可用组件列表")


class SceneConfigResponse(BaseModel):
    """场景配置响应"""

    scene_type: str = Field(..., description="场景类型")
    name: str = Field(..., description="场景名称")
    name_en: str = Field(..., description="场景英文名")
    icon: str = Field(..., description="图标标识")
    primary_color: str = Field(..., description="主题色")
    description: Optional[str] = Field(default=None, description="场景描述")
    layout_config: Optional[Dict[str, Any]] = Field(default=None, description="布局配置")
    feature_flags: Optional[Dict[str, bool]] = Field(default=None, description="功能开关")
    default_widgets: Optional[List[str]] = Field(default=None, description="默认组件")
    ai_prompt_template: Optional[str] = Field(default=None, description="AI提示词模板")


class SceneRecommendation(BaseModel):
    """场景推荐响应"""

    recommended_scene: str = Field(..., description="推荐场景类型")
    reason: str = Field(..., description="推荐理由")
    confidence: float = Field(..., ge=0, le=1, description="推荐置信度")
    alternative_scenes: Optional[List[str]] = Field(default=None, description="备选场景")
    time_context: Optional[str] = Field(default=None, description="时间上下文信息")
