"""
智慧学伴 分页工具
"""
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResult(BaseModel, Generic[T]):
    """分页结果"""

    items: List[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")
    total_pages: int = Field(default=0, description="总页数")

    def __init__(self, **data):
        super().__init__(**data)
        if self.total > 0 and self.page_size > 0:
            self.total_pages = (self.total + self.page_size - 1) // self.page_size


def calculate_offset(page: int, page_size: int) -> int:
    """
    计算分页偏移量

    Args:
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        int: 偏移量
    """
    return (page - 1) * page_size


def calculate_total_pages(total: int, page_size: int) -> int:
    """
    计算总页数

    Args:
        total: 总记录数
        page_size: 每页数量

    Returns:
        int: 总页数
    """
    if page_size <= 0:
        return 0
    return (total + page_size - 1) // page_size


def build_pagination_response(
    items: List[Any],
    total: int,
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    """
    构建分页响应字典

    Args:
        items: 数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页数量

    Returns:
        Dict: 分页响应字典
    """
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": calculate_total_pages(total, page_size),
    }
