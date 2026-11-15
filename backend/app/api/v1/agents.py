"""
智慧学伴 AI智能体 API
提供AI对话、会话管理、智能体配置、多模型路由、场景预设等端点
"""
import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.agent import AgentMessage, AgentSession
from app.models.user import User
from app.schemas.agent import (
    AgentTypeResponse,
    IntentResult,
    MessageCreate,
    ModelBalancerResponse,
    ModelInfoResponse,
    ScenePresetResponse,
    SessionCreate,
    SessionResponse,
)
from app.schemas.common import APIResponse, PaginationParams, PaginatedResponse
from app.agents.intent_router import IntentRouter, IntentType, intent_router
from app.agents.scene_config import SCENE_PRESETS, get_scene_preset

logger = logging.getLogger(__name__)

router = APIRouter()

# 可用智能体类型列表
AGENT_TYPES = [
    AgentTypeResponse(
        agent_type="rag",
        name="知识问答",
        description="基于知识图谱和检索的知识问答",
        icon="Search",
        supported_features=["知识检索", "流式回答", "图谱关联"],
    ),
    AgentTypeResponse(
        agent_type="subject",
        name="学科专家",
        description="数学/物理/化学等专业解题",
        icon="Calculator",
        supported_features=["专业解题", "多步骤推导", "学科知识"],
    ),
    AgentTypeResponse(
        agent_type="quiz",
        name="测验出题",
        description="生成选择题/填空题/问答题",
        icon="Edit",
        supported_features=["自动出题", "多难度", "多题型"],
    ),
    AgentTypeResponse(
        agent_type="file_rag",
        name="文件解析",
        description="解析PDF/Word/PPT文件",
        icon="FileText",
        supported_features=["文件解析", "内容问答", "知识点提取"],
    ),
    AgentTypeResponse(
        agent_type="lesson_plan",
        name="备课助手",
        description="生成教案和教学计划",
        icon="BookOpen",
        supported_features=["教案生成", "教学设计", "目标设定"],
    ),
    AgentTypeResponse(
        agent_type="buddy",
        name="学伴",
        description="陪伴式学习对话",
        icon="Heart",
        supported_features=["学习陪伴", "鼓励互动", "情绪支持"],
    ),
    AgentTypeResponse(
        agent_type="diagnosis",
        name="学习诊断",
        description="知识掌握度诊断分析",
        icon="Activity",
        supported_features=["IRT诊断", "弱点分析", "学习路径"],
    ),
    AgentTypeResponse(
        agent_type="classroom",
        name="课堂管理",
        description="课堂互动辅助",
        icon="Users",
        supported_features=["互动建议", "出题", "参与度分析"],
    ),
    AgentTypeResponse(
        agent_type="psychology",
        name="心理支持",
        description="学习心理建议和压力疏导",
        icon="Smile",
        supported_features=["压力疏导", "情绪识别", "危机干预"],
    ),
    AgentTypeResponse(
        agent_type="anti_misconception",
        name="概念纠偏",
        description="识别常见错误概念并纠正",
        icon="AlertTriangle",
        supported_features=["错误识别", "概念纠正", "正确理解"],
    ),
    AgentTypeResponse(
        agent_type="general",
        name="通用助手",
        description="处理其他类型的请求",
        icon="MessageCircle",
        supported_features=["通用问答", "导航推荐"],
    ),
]


@router.get("/sessions", summary="获取AI会话列表")
async def list_sessions(
    pagination: PaginationParams = Depends(),
    agent_type: Optional[str] = Query(None, description="智能体类型筛选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取当前用户的AI会话列表"""
    from sqlalchemy import and_, desc, func, select

    conditions = [
        AgentSession.user_id == current_user.id,
        AgentSession.is_archived == False,
    ]
    if agent_type:
        conditions.append(AgentSession.agent_type == agent_type)

    # 总数
    count_stmt = select(func.count(AgentSession.id)).where(and_(*conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # 数据
    stmt = (
        select(AgentSession)
        .where(and_(*conditions))
        .order_by(desc(AgentSession.updated_at))
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    items = [
        {
            "id": s.id,
            "agent_type": s.agent_type,
            "title": s.title,
            "scene_type": s.scene_type,
            "model_name": s.model_name,
            "message_count": s.message_count,
            "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]

    return APIResponse(
        code=0,
        data=PaginatedResponse(
            items=items, total=total, page=pagination.page, page_size=pagination.page_size
        ),
        message="success",
    )


@router.post("/sessions", summary="创建AI会话")
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    创建新的AI对话会话

    当传入 scene_type 时，自动从场景预设加载：
    - system_prompt ← 预设模板
    - model_name ← LLMRouter 根据场景偏好选择
    - agent_type ← 若未指定，则用预设的 default_agent_type
    """
    from app.agents.llm_router import llm_router

    # 场景预设处理
    system_prompt: Optional[str] = None
    model_name: str = session_data.model_name or "gpt-4o"
    agent_type: str = session_data.agent_type or "rag"

    if session_data.scene_type:
        preset = get_scene_preset(session_data.scene_type)
        if preset:
            system_prompt = preset.system_prompt
            # 如果未指定 agent_type 或为默认值，使用场景预设的默认类型
            if not session_data.agent_type or session_data.agent_type == "rag":
                agent_type = preset.default_agent_type
            # 通过 LLMRouter 获取场景偏好模型
            try:
                await llm_router._initialize()
                model_provider = await llm_router.get_model(
                    scene_type=session_data.scene_type
                )
                if model_provider:
                    model_name = model_provider.model_name
            except Exception as e:
                logger.warning("获取场景偏好模型失败: %s, 使用默认模型", e)

    session = AgentSession(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        agent_type=agent_type,
        title=session_data.title or f"{agent_type}会话",
        scene_type=session_data.scene_type,
        course_id=session_data.course_id,
        model_name=model_name,
        system_prompt=system_prompt,
        context=json.dumps(session_data.context, ensure_ascii=False) if session_data.context else None,
    )
    db.add(session)
    await db.flush()

    return APIResponse(
        code=0,
        data={
            "id": session.id,
            "agent_type": session.agent_type,
            "scene_type": session.scene_type,
            "title": session.title,
            "model_name": session.model_name,
            "system_prompt": session.system_prompt,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        },
        message="success",
    )


@router.get("/sessions/{session_id}", summary="获取会话详情")
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取AI会话详情（含消息历史）"""
    from sqlalchemy import select

    stmt = select(AgentSession).where(AgentSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 获取消息历史
    msg_stmt = (
        select(AgentMessage)
        .where(AgentMessage.session_id == session_id)
        .order_by(AgentMessage.created_at)
    )
    msg_result = await db.execute(msg_stmt)
    messages = msg_result.scalars().all()

    return APIResponse(
        code=0,
        data={
            "id": session.id,
            "agent_type": session.agent_type,
            "title": session.title,
            "message_count": session.message_count,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "content_type": m.content_type,
                    "model_name": m.model_name,
                    "metadata": json.loads(m.metadata_json) if m.metadata_json else None,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        },
        message="success",
    )


@router.post("/sessions/{session_id}/messages", summary="发送消息")
async def send_message(
    session_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    向AI会话发送消息并获取回复

    改造点：
    1. 意图路由时传入 scene_type 上下文
    2. Agent context 中注入 db、user_id、tenant_id、course_id、scene_type
    3. Agent 内部通过 ResourceContextBuilder 构建资源上下文
    4. AI 消息 metadata_json 存储 citations + context_summary + model_fallback
    5. 返回完整响应（含引用来源、上下文摘要、模型信息）
    """
    from sqlalchemy import select

    # 获取会话
    stmt = select(AgentSession).where(AgentSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 如果会话有 scene_type 且有 system_prompt，在 context 中传递
    scene_type = session.scene_type

    # 保存用户消息
    user_msg = AgentMessage(
        session_id=session_id,
        role="user",
        content=message_data.content,
        content_type=message_data.content_type,
    )
    db.add(user_msg)

    # 意图路由（传入 scene_type 上下文）
    detected_intent = intent_router.route(
        message_data.content,
        context={"current_agent_type": session.agent_type, "scene_type": scene_type},
    )
    agent_type_str = intent_router.get_agent_type(detected_intent)

    # 获取对应Agent
    agent = _get_agent_instance(agent_type_str)

    # 获取历史消息
    msg_stmt = (
        select(AgentMessage)
        .where(AgentMessage.session_id == session_id)
        .order_by(AgentMessage.created_at)
    )
    msg_result = await db.execute(msg_stmt)
    history = msg_result.scalars().all()

    messages = [
        {"role": m.role, "content": m.content}
        for m in history
    ]

    # 构建 Agent context（注入 db、user_id、course_id、scene_type 等）
    agent_context: Dict[str, Any] = {
        "user_id": current_user.id,
        "tenant_id": current_user.tenant_id,
        "session_id": session_id,
        "course_id": session.course_id,
        "scene_type": scene_type,
        "db": db,
    }

    # 如果会话有预设 system_prompt，注入到 context
    if session.system_prompt:
        agent_context["system_prompt_override"] = session.system_prompt

    # 调用Agent（内部通过 ResourceContextBuilder + LLMRouter）
    agent_result = await agent.execute(
        messages=messages,
        context=agent_context,
    )

    # 提取引用来源和上下文摘要
    citations = agent_result.get("citations", [])
    context_summary = agent_result.get("context_summary", {
        "notes_count": 0,
        "resources_count": 0,
        "graph_nodes_count": 0,
        "teacher_methods_count": 0,
    })
    model_used = agent_result.get("model", "")
    model_fallback = agent_result.get("model_fallback", False)
    fallback_info = agent_result.get("fallback_info")

    # 构建 metadata_json
    metadata = {
        "citations": citations,
        "context_summary": context_summary,
        "model_used": model_used,
        "model_fallback": model_fallback,
    }
    if fallback_info:
        metadata["fallback_info"] = fallback_info

    # 保存AI回复
    ai_msg = AgentMessage(
        session_id=session_id,
        role="assistant",
        content=agent_result.get("content", ""),
        content_type="markdown",
        model_name=model_used,
        metadata_json=json.dumps(metadata, ensure_ascii=False),
    )
    db.add(ai_msg)

    # 更新会话
    session.message_count += 2
    session.last_message_at = datetime.datetime.utcnow()
    # 更新 token 消耗
    usage = agent_result.get("tokens", {})
    if isinstance(usage, dict):
        session.total_tokens += usage.get("total_tokens", 0)
    await db.flush()

    return APIResponse(
        code=0,
        data={
            "user_message": {
                "id": user_msg.id,
                "role": "user",
                "content": message_data.content,
            },
            "assistant_message": {
                "id": ai_msg.id,
                "role": "assistant",
                "content": agent_result.get("content", ""),
                "model_name": model_used,
            },
            "citations": citations,
            "context_summary": context_summary,
            "model_used": model_used,
            "model_fallback": model_fallback,
            "detected_intent": detected_intent.value,
            "agent_type": agent_type_str,
        },
        message="success",
    )


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """删除AI会话"""
    from sqlalchemy import select

    stmt = select(AgentSession).where(AgentSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    session.is_archived = True
    await db.flush()

    return APIResponse(code=0, data=None, message="会话已归档")


@router.get("/types", summary="获取智能体类型列表")
async def list_agent_types() -> APIResponse:
    """获取所有可用的AI智能体类型"""
    return APIResponse(
        code=0,
        data=[t.model_dump() for t in AGENT_TYPES],
        message="success",
    )


@router.post("/intent", summary="意图识别")
async def detect_intent(
    text: str = Query(..., description="待识别文本"),
) -> APIResponse:
    """识别用户输入的意图"""
    detected = intent_router.route(text)
    agent_type = intent_router.get_agent_type(detected)

    return APIResponse(
        code=0,
        data=IntentResult(
            intent=detected.value,
            agent_type=agent_type,
            confidence=1.0,
        ).model_dump(),
        message="success",
    )


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: int):
    """
    WebSocket 实时对话端点

    改造点：
    1. 接收消息后，先发送 context 消息告知前端注入了哪些资源
    2. 流式输出 chunks
    3. done 消息中携带 model_used、model_fallback、citations
    """
    await websocket.accept()
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "消息格式错误"})
                continue

            content = data.get("content", "")
            if not content:
                continue

            # 意图路由
            detected_intent = intent_router.route(content)
            agent_type_str = intent_router.get_agent_type(detected_intent)
            agent = _get_agent_instance(agent_type_str)

            # 查询会话信息并保存用户消息
            from sqlalchemy import select as sa_select
            from app.database import async_session_factory

            session_info: Dict[str, Any] = {}
            try:
                async with async_session_factory() as db:
                    stmt = sa_select(AgentSession).where(AgentSession.id == session_id)
                    result = await db.execute(stmt)
                    session = result.scalars().first()
                    if session:
                        session_info = {
                            "user_id": session.user_id,
                            "tenant_id": session.tenant_id,
                            "course_id": session.course_id,
                            "scene_type": session.scene_type,
                            "model_name": session.model_name,
                        }
                        # 保存用户消息到 agent_messages 表
                        user_msg = AgentMessage(
                            session_id=session_id,
                            role="user",
                            content=content,
                            content_type="text",
                        )
                        db.add(user_msg)
                        await db.flush()
                        await db.commit()
            except Exception as e:
                logger.warning("WebSocket 查询会话/保存用户消息失败: %s", e)

            # 构建资源上下文
            citations: List[Dict[str, Any]] = []
            context_summary: Dict[str, Any] = {}
            if session_info.get("user_id"):
                try:
                    from app.agents.resource_context import resource_context_builder

                    async with async_session_factory() as ctx_db:
                        context_result = await resource_context_builder.build(
                            db=ctx_db,
                            user_id=session_info["user_id"],
                            tenant_id=session_info.get("tenant_id", 0),
                            course_id=session_info.get("course_id"),
                            query=content,
                            scene_type=session_info.get("scene_type"),
                        )
                        citations = resource_context_builder.citations_to_dicts(
                            context_result.citations
                        )
                        context_summary = context_result.summary
                except Exception as e:
                    logger.error("WebSocket 资源上下文构建失败: %s", e)

            # 发送 context 消息
            if context_summary:
                await websocket.send_json({
                    "type": "context",
                    "summary": context_summary,
                })

            # 构建 agent context
            agent_context: Dict[str, Any] = {
                "user_id": session_info.get("user_id"),
                "tenant_id": session_info.get("tenant_id"),
                "session_id": session_id,
                "course_id": session_info.get("course_id"),
                "scene_type": session_info.get("scene_type"),
                "citations": citations,
                "context_summary": context_summary,
            }

            # 流式输出（同时累积完整回复内容用于持久化）
            streaming_parts: List[str] = []
            async for chunk in agent.stream_execute(
                messages=[{"role": "user", "content": content}],
                context=agent_context,
            ):
                streaming_parts.append(chunk)
                await websocket.send_json({
                    "type": "chunk",
                    "content": chunk,
                    "agent_type": agent_type_str,
                })
            streaming_content = "".join(streaming_parts)

            # 保存 AI 回复并更新会话统计信息
            model_used = session_info.get("model_name", "")
            metadata = {
                "citations": citations,
                "context_summary": context_summary,
                "model_used": model_used,
                "model_fallback": False,
            }
            try:
                async with async_session_factory() as db:
                    stmt = sa_select(AgentSession).where(AgentSession.id == session_id)
                    result = await db.execute(stmt)
                    session_obj = result.scalars().first()
                    if session_obj:
                        # 保存 assistant 消息
                        ai_msg = AgentMessage(
                            session_id=session_id,
                            role="assistant",
                            content=streaming_content,
                            content_type="markdown",
                            model_name=model_used,
                            metadata_json=json.dumps(metadata, ensure_ascii=False),
                        )
                        db.add(ai_msg)

                        # 更新会话统计信息
                        session_obj.message_count += 2
                        session_obj.last_message_at = datetime.datetime.utcnow()
                        # 流式模式无精确 usage，按字符数粗略估算 token
                        estimated_input = int(len(content) * 1.5)
                        estimated_output = int(len(streaming_content) * 1.5)
                        session_obj.total_tokens += estimated_input + estimated_output

                        await db.flush()
                        await db.commit()
            except Exception as e:
                logger.error("WebSocket 保存 AI 回复失败: %s", e)

            # done 消息携带 citations 和模型信息
            await websocket.send_json({
                "type": "done",
                "agent_type": agent_type_str,
                "citations": citations,
                "context_summary": context_summary,
                "model_used": model_used,
            })
    except Exception as e:
        logger.error("WebSocket 异常: %s", e)
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/models", summary="获取可用模型列表及状态")
async def list_models(
    current_user: User = Depends(get_current_user),
) -> APIResponse:
    """
    获取可用模型列表及健康状态

    返回每个模型提供商的配置状态和可用性，
    用于前端模型状态指示灯和模型选择器。
    """
    from app.agents.llm_router import llm_router

    try:
        health_list = await llm_router.health_check()
        return APIResponse(
            code=0,
            data=health_list,
            message="success",
        )
    except Exception as e:
        logger.error("获取模型列表失败: %s", e)
        return APIResponse(code=0, data=[], message="success")


@router.get("/scenes", summary="获取场景预设配置列表")
async def list_scenes(
    current_user: User = Depends(get_current_user),
) -> APIResponse:
    """
    获取场景预设配置列表

    返回 4 类预设场景（自习/预习/复习/冲刺）的配置信息，
    用于前端场景入口页渲染。
    """
    scenes = [
        {
            "scene_type": preset.scene_type,
            "name": preset.name,
            "description": preset.description,
            "icon": preset.icon,
            "preferred_model": preset.preferred_model,
            "default_agent_type": preset.default_agent_type,
        }
        for preset in SCENE_PRESETS.values()
    ]
    return APIResponse(code=0, data=scenes, message="success")


@router.get("/sessions/{session_id}/context", summary="获取会话上下文资源")
async def get_session_context(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """
    获取当前会话注入的上下文资源列表

    调用 ResourceContextBuilder 构建完整的资源上下文，
    返回笔记/资源/图谱节点/老师方法列表及摘要。
    """
    from sqlalchemy import select

    # 验证会话归属
    stmt = select(AgentSession).where(AgentSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 构建资源上下文
    from app.agents.resource_context import resource_context_builder

    try:
        context_result = await resource_context_builder.build(
            db=db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id or 0,
            course_id=session.course_id,
            scene_type=session.scene_type,
        )
        return APIResponse(
            code=0,
            data={
                "notes": context_result.raw_notes,
                "resources": context_result.raw_resources,
                "graph_nodes": context_result.raw_graph_nodes,
                "teacher_methods": context_result.raw_teacher_methods,
                "citations": resource_context_builder.citations_to_dicts(
                    context_result.citations
                ),
                "summary": context_result.summary,
            },
            message="success",
        )
    except Exception as e:
        logger.error("获取会话上下文失败: %s", e)
        return APIResponse(
            code=0,
            data={
                "notes": [],
                "resources": [],
                "graph_nodes": [],
                "teacher_methods": [],
                "citations": [],
                "summary": {
                    "notes_count": 0,
                    "resources_count": 0,
                    "graph_nodes_count": 0,
                    "teacher_methods_count": 0,
                },
            },
            message="success",
        )


@router.get("/models/balancer", summary="获取模型负载均衡状态")
async def get_model_balancer_status(
    current_user: User = Depends(get_current_user),
) -> APIResponse:
    """
    获取模型负载均衡状态

    返回各 Provider 的健康指标（avg_latency_ms, success_rate, failure_count），
    当前负载均衡策略（latency/weighted/sticky），
    以及推荐模型（sticky 策略下）。

    用于管理员监控模型健康状态和负载分布。
    """
    from app.agents.llm_router import llm_router
    from app.config import settings

    await llm_router._initialize()

    providers_status = llm_router.get_balancer_status()
    current_strategy = settings.LLM_BALANCER_STRATEGY

    # sticky 策略下返回推荐模型
    recommended_model: Optional[str] = None
    if current_strategy == "sticky":
        # 找第一个可用的已配置 provider
        for p in providers_status:
            if p.get("is_available") and p.get("is_configured"):
                recommended_model = p.get("model_name")
                break

    response = ModelBalancerResponse(
        providers=providers_status,
        current_strategy=current_strategy,
        recommended_model=recommended_model,
    )

    return APIResponse(
        code=0,
        data=response.model_dump(),
        message="success",
    )


def _get_agent_instance(agent_type: str):
    """根据agent_type获取Agent实例"""
    from app.agents.rag_agent import RAGAgent
    from app.agents.subject_agent import SubjectAgent
    from app.agents.quiz_agent import QuizAgent
    from app.agents.file_rag_agent import FileRAGAgent
    from app.agents.lesson_plan_agent import LessonPlanAgent
    from app.agents.buddy_agent import BuddyAgent
    from app.agents.diagnosis_agent import DiagnosisAgent
    from app.agents.classroom_agent import ClassroomAgent
    from app.agents.psychology_agent import PsychologyAgent
    from app.agents.anti_misconception_agent import AntiMisconceptionAgent
    from app.agents.general_agent import GeneralAgent

    agent_map = {
        "rag": RAGAgent,
        "subject": SubjectAgent,
        "quiz": QuizAgent,
        "file_rag": FileRAGAgent,
        "lesson_plan": LessonPlanAgent,
        "buddy": BuddyAgent,
        "diagnosis": DiagnosisAgent,
        "classroom": ClassroomAgent,
        "psychology": PsychologyAgent,
        "anti_misconception": AntiMisconceptionAgent,
        "general": GeneralAgent,
    }

    agent_class = agent_map.get(agent_type, GeneralAgent)
    return agent_class()
