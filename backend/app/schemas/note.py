"""
智慧学伴 笔记Schema
NoteCreate / NoteUpdate / NoteResponse / NoteVersionResponse / ShareResponse
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    """创建笔记请求"""

    title: str = Field(..., description="笔记标题", min_length=1, max_length=300)
    content: Optional[str] = Field(None, description="笔记内容(富文本/Markdown)")
    content_plain: Optional[str] = Field(None, description="纯文本内容")
    note_type: str = Field("personal", description="笔记类型: personal/course/ai_generated")
    course_id: Optional[int] = Field(None, description="关联课程ID")
    resource_id: Optional[int] = Field(None, description="关联资源ID")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_encrypted: bool = Field(False, description="是否启用E2E加密")


class NoteUpdate(BaseModel):
    """更新笔记请求"""

    title: Optional[str] = Field(None, description="笔记标题", max_length=300)
    content: Optional[str] = Field(None, description="笔记内容")
    content_plain: Optional[str] = Field(None, description="纯文本内容")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    change_summary: Optional[str] = Field(None, description="变更摘要", max_length=500)


class NoteResponse(BaseModel):
    """笔记响应"""

    id: int = Field(..., description="笔记ID")
    tenant_id: int = Field(..., description="租户ID")
    title: str = Field(..., description="笔记标题")
    content: Optional[str] = Field(None, description="笔记内容")
    note_type: str = Field(..., description="笔记类型")
    course_id: Optional[int] = Field(None, description="关联课程ID")
    resource_id: Optional[int] = Field(None, description="关联资源ID")
    owner_id: int = Field(..., description="所有者ID")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    ai_enhanced: bool = Field(False, description="是否经过AI增强")
    share_code: Optional[str] = Field(None, description="分享码")
    word_count: int = Field(0, description="字数")
    version: int = Field(1, description="版本号")
    is_deleted: bool = Field(False, description="是否已删除")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class NoteVersionResponse(BaseModel):
    """笔记版本响应"""

    id: int = Field(..., description="版本ID")
    note_id: int = Field(..., description="笔记ID")
    version: int = Field(..., description="版本号")
    title: str = Field(..., description="版本标题")
    content: Optional[str] = Field(None, description="版本内容")
    change_summary: Optional[str] = Field(None, description="变更摘要")
    created_by: int = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")


class ShareResponse(BaseModel):
    """笔记分享响应"""

    share_code: str = Field(..., description="分享码")
    share_url: str = Field(..., description="分享链接")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class AIEnhanceRequest(BaseModel):
    """AI增强笔记请求"""

    enhance_type: str = Field(
        "summary",
        description="增强类型: summary/correct/expand/mindmap",
    )
    additional_instructions: Optional[str] = Field(None, description="额外指令")


class AIEnhanceResponse(BaseModel):
    """AI增强笔记响应"""

    enhanced_content: str = Field(..., description="增强后的内容")
    enhance_type: str = Field(..., description="增强类型")
    original_word_count: int = Field(0, description="原始字数")
    enhanced_word_count: int = Field(0, description="增强后字数")
