"""
智慧学伴 Agent相关Schema
SessionCreate / SessionResponse / MessageCreate / MessageResponse / AgentTypeResponse
新增: ModelInfoResponse / ScenePresetResponse / CitationSchema / ContextSummary / SendMessageResponse / SessionContextResponse
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """创建AI会话请求"""

    agent_type: Optional[str] = Field(None, description="智能体类型（scene_type 存在时可由预设决定）", max_length=30)
    title: Optional[str] = Field(None, description="会话标题", max_length=200)
    scene_type: Optional[str] = Field(None, description="场景类型", max_length=30)
    course_id: Optional[int] = Field(None, description="关联课程ID")
    model_name: Optional[str] = Field(None, description="模型名称", max_length=50)
    context: Optional[Dict[str, Any]] = Field(None, description="会话上下文(JSON)")


class SessionResponse(BaseModel):
    """AI会话响应"""

    id: int = Field(..., description="会话ID")
    tenant_id: int = Field(..., description="租户ID")
    user_id: int = Field(..., description="用户ID")
    agent_type: str = Field(..., description="智能体类型")
    title: Optional[str] = Field(None, description="会话标题")
    scene_type: Optional[str] = Field(None, description="场景类型")
    course_id: Optional[int] = Field(None, description="关联课程ID")
    model_name: str = Field(..., description="模型名称")
    message_count: int = Field(0, description="消息数量")
    total_tokens: int = Field(0, description="总Token消耗")
    is_archived: bool = Field(False, description="是否归档")
    last_message_at: Optional[datetime] = Field(None, description="最后消息时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class MessageCreate(BaseModel):
    """发送消息请求"""

    content: str = Field(..., description="消息内容", min_length=1)
    content_type: str = Field("text", description="内容类型: text/markdown/code/image")
    stream: bool = Field(False, description="是否流式输出")


class MessageResponse(BaseModel):
    """AI消息响应"""

    id: int = Field(..., description="消息ID")
    session_id: int = Field(..., description="会话ID")
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")
    content_type: str = Field("text", description="内容类型")
    tokens: int = Field(0, description="Token数量")
    model_name: Optional[str] = Field(None, description="使用的模型")
    created_at: datetime = Field(..., description="创建时间")


class AgentTypeResponse(BaseModel):
    """智能体类型响应"""

    agent_type: str = Field(..., description="智能体类型标识")
    name: str = Field(..., description="智能体名称")
    description: str = Field(..., description="智能体描述")
    icon: Optional[str] = Field(None, description="图标")
    supported_features: List[str] = Field(default_factory=list, description="支持的功能")


class IntentResult(BaseModel):
    """意图识别结果"""

    intent: str = Field(..., description="意图类型")
    agent_type: str = Field(..., description="对应的Agent类型")
    confidence: float = Field(1.0, description="置信度")


# ============ 多模型路由相关 Schema ============


class ModelInfoResponse(BaseModel):
    """模型信息响应"""

    provider: str = Field(..., description="提供商: deepseek/qwen/hunyuan")
    model: str = Field(..., description="模型名称")
    status: str = Field(..., description="状态: available/unavailable/not_configured")
    is_default: bool = Field(False, description="是否默认首选")
    is_configured: bool = Field(True, description="是否已配置API Key")


class ScenePresetResponse(BaseModel):
    """场景预设响应"""

    scene_type: str = Field(..., description="场景类型")
    name: str = Field(..., description="场景名称")
    description: str = Field(..., description="场景描述")
    icon: str = Field(..., description="图标")
    preferred_model: str = Field(..., description="偏好模型")


class CitationSchema(BaseModel):
    """引用来源"""

    type: str = Field(..., description="类型: note/resource/teacher_method/graph_node")
    title: str = Field(..., description="标题")
    source_url: str = Field(..., description="跳转路径")
    teacher_name: Optional[str] = Field(None, description="教师名(仅teacher_method)")


class ContextSummary(BaseModel):
    """上下文摘要"""

    notes_count: int = Field(0, description="笔记数")
    resources_count: int = Field(0, description="资源数")
    graph_nodes_count: int = Field(0, description="图谱节点数")
    teacher_methods_count: int = Field(0, description="老师方法数")


class SendMessageResponse(BaseModel):
    """发送消息响应（改造）"""

    user_message: Dict[str, Any] = Field(..., description="用户消息")
    assistant_message: Dict[str, Any] = Field(..., description="AI消息")
    citations: List[CitationSchema] = Field(default_factory=list, description="引用来源")
    context_summary: ContextSummary = Field(default_factory=ContextSummary, description="上下文摘要")
    model_used: str = Field("", description="使用的模型")
    model_fallback: bool = Field(False, description="是否发生了模型切换")


class SessionContextResponse(BaseModel):
    """会话上下文响应"""

    notes: List[Dict[str, Any]] = Field(default_factory=list)
    resources: List[Dict[str, Any]] = Field(default_factory=list)
    graph_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    teacher_methods: List[Dict[str, Any]] = Field(default_factory=list)
    summary: ContextSummary = Field(default_factory=ContextSummary)


# ============ v2 新增：负载均衡相关 Schema ============


class ModelBalancerResponse(BaseModel):
    """模型负载均衡状态响应"""

    providers: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="各 provider 健康状态列表",
    )
    current_strategy: str = Field(
        "latency", description="当前负载均衡策略: latency/weighted/sticky"
    )
    recommended_model: Optional[str] = Field(
        None, description="推荐模型（sticky 策略下）"
    )
