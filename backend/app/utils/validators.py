"""
智慧学伴 校验工具
"""
import re
from typing import Optional

from pydantic import field_validator


def validate_email(email: str) -> bool:
    """
    校验邮箱格式

    Args:
        email: 邮箱地址

    Returns:
        bool: 是否有效
    """
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    校验中国大陆手机号格式

    Args:
        phone: 手机号

    Returns:
        bool: 是否有效
    """
    pattern = r"^1[3-9]\d{9}$"
    return bool(re.match(pattern, phone))


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    校验密码强度

    要求：
    - 至少6位
    - 包含字母和数字

    Args:
        password: 密码

    Returns:
        tuple: (是否有效, 错误消息)
    """
    if len(password) < 6:
        return False, "密码长度至少6位"
    if len(password) > 50:
        return False, "密码长度不能超过50位"
    if not re.search(r"[a-zA-Z]", password):
        return False, "密码必须包含字母"
    if not re.search(r"\d", password):
        return False, "密码必须包含数字"
    return True, None


def validate_scene_type(scene_type: str) -> bool:
    """
    校验场景类型

    Args:
        scene_type: 场景类型

    Returns:
        bool: 是否有效
    """
    valid_types = {"classroom", "self_study", "exam", "discussion"}
    return scene_type in valid_types


def validate_role(role: str) -> bool:
    """
    校验用户角色

    Args:
        role: 角色标识

    Returns:
        bool: 是否有效
    """
    valid_roles = {"student", "teacher", "admin", "super_admin"}
    return role in valid_roles


def validate_nickname(nickname: str) -> tuple[bool, Optional[str]]:
    """
    校验昵称

    Args:
        nickname: 昵称

    Returns:
        tuple: (是否有效, 错误消息)
    """
    if len(nickname) < 2:
        return False, "昵称至少2个字符"
    if len(nickname) > 50:
        return False, "昵称不能超过50个字符"
    return True, None
