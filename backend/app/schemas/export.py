"""
智慧学伴 对话导出相关 Pydantic Schema
v2 新增：对话导出 PDF/Markdown
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExportCreate(BaseModel):
    """创建导出任务请求"""

    export_format: str = Field(..., description="导出格式: pdf/markdown")


class ExportResponse(BaseModel):
    """导出记录响应"""

    id: int = Field(..., description="导出ID")
    session_id: int = Field(..., description="会话ID")
    export_format: str = Field(..., description="导出格式")
    status: str = Field(..., description="状态: pending/processing/completed/failed")
    file_size: int = Field(0, description="文件大小(字节)")
    error_msg: Optional[str] = Field(None, description="错误信息")
    created_at: Optional[str] = Field(None, description="创建时间")
    completed_at: Optional[str] = Field(None, description="完成时间")
    expired_at: Optional[str] = Field(None, description="过期时间")

    class Config:
        from_attributes = True


class ExportDownloadResponse(BaseModel):
    """导出下载链接响应"""

    download_url: str = Field(..., description="预签名下载 URL")
    expired_at: str = Field(..., description="过期时间")
