"""
智慧学伴 数据分类分级模块
定义4级数据分类（公开/内部/敏感/机密），敏感数据检测规则
"""
import logging
import re
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DataClassification(IntEnum):
    """数据分类分级（4级）"""

    PUBLIC = 1       # 公开：可对外公开的数据
    INTERNAL = 2     # 内部：仅限内部使用
    SENSITIVE = 3    # 敏感：包含个人信息或重要业务数据
    CONFIDENTIAL = 4 # 机密：核心数据，严格限制访问


# 分级描述
CLASSIFICATION_LABELS: Dict[DataClassification, str] = {
    DataClassification.PUBLIC: "公开",
    DataClassification.INTERNAL: "内部",
    DataClassification.SENSITIVE: "敏感",
    DataClassification.CONFIDENTIAL: "机密",
}

# 分级颜色标识（用于前端展示）
CLASSIFICATION_COLORS: Dict[DataClassification, str] = {
    DataClassification.PUBLIC: "#4CAF50",
    DataClassification.INTERNAL: "#2196F3",
    DataClassification.SENSITIVE: "#FF9800",
    DataClassification.CONFIDENTIAL: "#F44336",
}


# 敏感数据检测规则
SENSITIVE_DATA_RULES: List[Dict[str, Any]] = [
    {
        "name": "身份证号",
        "field_names": {"id_card", "id_number", "identity_card", "身份证"},
        "pattern": r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
        "classification": DataClassification.SENSITIVE,
        "mask_template": "**** **** **** {}",
    },
    {
        "name": "手机号",
        "field_names": {"phone", "mobile", "telephone", "手机号", "电话"},
        "pattern": r"1[3-9]\d{9}",
        "classification": DataClassification.SENSITIVE,
        "mask_template": "****{}",
    },
    {
        "name": "邮箱地址",
        "field_names": {"email", "mail", "邮箱"},
        "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "classification": DataClassification.INTERNAL,
        "mask_template": "***@***.***",
    },
    {
        "name": "银行卡号",
        "field_names": {"bank_card", "bank_account", "银行卡"},
        "pattern": r"\d{16,19}",
        "classification": DataClassification.CONFIDENTIAL,
        "mask_template": "**** **** **** {}",
    },
    {
        "name": "密码",
        "field_names": {"password", "passwd", "secret", "密码", "密钥"},
        "pattern": None,  # 不做内容匹配，仅按字段名
        "classification": DataClassification.CONFIDENTIAL,
        "mask_template": "******",
    },
    {
        "name": "地址",
        "field_names": {"address", "地址", "住址"},
        "pattern": None,
        "classification": DataClassification.SENSITIVE,
        "mask_template": "***省***市***",
    },
    {
        "name": "成绩",
        "field_names": {"score", "grade", "gpa", "成绩", "分数"},
        "pattern": None,
        "classification": DataClassification.SENSITIVE,
        "mask_template": "**",
    },
]

# 资源类型默认分级
RESOURCE_DEFAULT_CLASSIFICATION: Dict[str, DataClassification] = {
    "user_profile": DataClassification.SENSITIVE,
    "user_auth": DataClassification.CONFIDENTIAL,
    "course_content": DataClassification.INTERNAL,
    "student_record": DataClassification.SENSITIVE,
    "teacher_record": DataClassification.SENSITIVE,
    "note": DataClassification.INTERNAL,
    "diagnosis": DataClassification.SENSITIVE,
    "audit_log": DataClassification.CONFIDENTIAL,
    "system_config": DataClassification.CONFIDENTIAL,
    "public_resource": DataClassification.PUBLIC,
    "notification": DataClassification.INTERNAL,
    "classroom": DataClassification.INTERNAL,
}


def classify_field(field_name: str, field_value: str = "") -> DataClassification:
    """
    根据字段名和值判断数据分级

    Args:
        field_name: 字段名
        field_value: 字段值

    Returns:
        数据分级
    """
    field_lower = field_name.lower()

    # 1. 按字段名匹配
    for rule in SENSITIVE_DATA_RULES:
        if field_lower in rule["field_names"]:
            return rule["classification"]

    # 2. 按内容模式匹配
    if field_value:
        for rule in SENSITIVE_DATA_RULES:
            pattern = rule.get("pattern")
            if pattern and re.search(pattern, str(field_value)):
                return rule["classification"]

    # 3. 默认内部级别
    return DataClassification.INTERNAL


def classify_resource(resource_type: str) -> DataClassification:
    """
    根据资源类型判断数据分级

    Args:
        resource_type: 资源类型

    Returns:
        数据分级
    """
    return RESOURCE_DEFAULT_CLASSIFICATION.get(
        resource_type, DataClassification.INTERNAL
    )


def detect_sensitive_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    检测数据中的敏感信息

    Args:
        data: 待检测的数据字典

    Returns:
        检测到的敏感信息列表，每条包含字段名、类型、分级
    """
    findings: List[Dict[str, Any]] = []

    for field_name, field_value in data.items():
        if field_value is None:
            continue

        value_str = str(field_value)
        field_lower = field_name.lower()

        # 按字段名检测
        for rule in SENSITIVE_DATA_RULES:
            if field_lower in rule["field_names"]:
                findings.append({
                    "field": field_name,
                    "type": rule["name"],
                    "classification": rule["classification"].value,
                    "classification_label": CLASSIFICATION_LABELS[rule["classification"]],
                    "detection_method": "field_name",
                })
                break
        else:
            # 按内容模式检测
            for rule in SENSITIVE_DATA_RULES:
                pattern = rule.get("pattern")
                if pattern and re.search(pattern, value_str):
                    findings.append({
                        "field": field_name,
                        "type": rule["name"],
                        "classification": rule["classification"].value,
                        "classification_label": CLASSIFICATION_LABELS[rule["classification"]],
                        "detection_method": "content_pattern",
                    })
                    break

    return findings


def mask_sensitive_value(field_name: str, field_value: str) -> str:
    """
    对敏感字段值进行脱敏处理

    Args:
        field_name: 字段名
        field_value: 原始值

    Returns:
        脱敏后的值
    """
    field_lower = field_name.lower()

    for rule in SENSITIVE_DATA_RULES:
        if field_lower in rule["field_names"]:
            template = rule.get("mask_template", "****")
            if template and field_value:
                # 简单脱敏：保留末4位
                if "{}" in template:
                    return template.format(field_value[-4:] if len(field_value) >= 4 else "****")
                return template

    return field_value


def get_classification_label(classification: DataClassification) -> str:
    """获取分级标签"""
    return CLASSIFICATION_LABELS.get(classification, "未知")


def get_classification_color(classification: DataClassification) -> str:
    """获取分级颜色"""
    return CLASSIFICATION_COLORS.get(classification, "#999999")
