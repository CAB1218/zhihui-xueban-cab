"""
AI4EDU 大模型服务商配置 ORM 模型

用途：让管理员在「AI 对话 → 模型配置」里直接填写 DeepSeek / 通义千问 / 混元的
API Key、API Base 与模型名，保存后立刻生效，不必改 .env 重启后端。

设计要点：
- API Key 用 AES-256-CBC（app.core.encryption.encrypt_field）加密存储，接口只回显掩码
- 一条记录 = 一个 provider 的「页面覆盖配置」；没有记录时回退到 backend/.env 的默认值
- 记录最近一次连通性测试结果，便于界面区分「已配置」与「已验证可用」
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LlmProviderConfig(Base):
    """大模型服务商配置（覆盖 .env 默认值）"""

    __tablename__ = "llm_provider_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="配置ID")
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True, comment="服务商: deepseek/qwen/hunyuan"
    )

    api_key_encrypted: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="API Key（AES 加密存储）"
    )
    api_base: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="API Base，如 https://api.deepseek.com/v1"
    )
    model_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="模型名，如 deepseek-chat"
    )

    # 最近一次「测试连接」的结果，用于界面区分「已配置」与「已验证可用」
    last_test_ok: Mapped[Optional[bool]] = mapped_column(
        nullable=True, comment="最近一次连通性测试是否通过"
    )
    last_test_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="最近一次测试的返回摘要或错误原因"
    )
    last_test_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="最近一次测试时间"
    )

    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="最后修改人用户ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )
