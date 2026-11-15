"""
智慧学伴 场景预设配置模块
定义 4 类学习场景的预设配置（自习/预习/复习/冲刺）
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ScenePreset:
    """场景预设配置"""

    scene_type: str  # "self_study" / "preview" / "review" / "exam_prep"
    name: str  # 显示名称
    description: str  # 场景描述
    icon: str  # Element Plus 图标名
    system_prompt: str  # 系统提示词模板
    preferred_model: str  # 模型偏好: "deepseek" / "qwen" / "hunyuan"
    default_agent_type: str  # 默认 Agent 类型: "rag" / "subject"


# 场景预设常量配置
SCENE_PRESETS: Dict[str, ScenePreset] = {
    "self_study": ScenePreset(
        scene_type="self_study",
        name="自习答疑",
        description="随时提问，基于你的笔记和学习资料解答疑问",
        icon="Reading",
        system_prompt=(
            "你是学生的自习助手。你的职责是基于学生的学习资料解答疑问，"
            "优先使用老师讲授的方法。\n\n"
            "回答要求：\n"
            "1. 优先使用【老师方法】段落中的解题方法和思路\n"
            "2. 结合【我的笔记】中的内容，体现学生当前的学习进度\n"
            "3. 引用【课程资源】中的教材/课件内容作为依据\n"
            "4. 回答末尾标注参考来源\n"
            "5. 如果老师方法不可用，回退到教材方法并标注\"未找到老师讲解记录\""
        ),
        preferred_model="deepseek",
        default_agent_type="rag",
    ),
    "preview": ScenePreset(
        scene_type="preview",
        name="课前预习",
        description="预习新内容，梳理核心概念和前置知识",
        icon="Search",
        system_prompt=(
            "你是预习向导。你的职责是帮学生梳理即将学习的内容，"
            "提供核心概念清单和前置知识检查。\n\n"
            "回答要求：\n"
            "1. 列出本节课的核心概念（3-5个）\n"
            "2. 检查前置知识掌握情况\n"
            "3. 提供3个引导性问题帮助学生思考\n"
            "4. 结合知识图谱展示知识点之间的关系"
        ),
        preferred_model="qwen",
        default_agent_type="rag",
    ),
    "review": ScenePreset(
        scene_type="review",
        name="课后复习",
        description="巩固今日所学，回顾课堂板书和笔记",
        icon="Edit",
        system_prompt=(
            "你是复习教练。你的职责是基于学生笔记和课堂板书，"
            "帮助学生巩固当天所学。\n\n"
            "回答要求：\n"
            "1. 优先使用老师课堂讲授的方法（【老师方法】段落）\n"
            "2. 结合学生的笔记内容查漏补缺\n"
            "3. 提供针对性练习建议\n"
            "4. 回答末尾标注参考来源，提供\"查看老师板书/录播片段\"链接"
        ),
        preferred_model="deepseek",
        default_agent_type="subject",
    ),
    "exam_prep": ScenePreset(
        scene_type="exam_prep",
        name="考前冲刺",
        description="查漏补缺，基于薄弱知识点生成针对性练习",
        icon="Trophy",
        system_prompt=(
            "你是冲刺导师。你的职责是基于学生薄弱知识点生成针对性练习和快速复习要点。\n\n"
            "回答要求：\n"
            "1. 分析学生的笔记标签和知识图谱覆盖情况\n"
            "2. 生成\"薄弱知识点 TOP5 + 针对练习题\"清单\n"
            "3. 练习题基于老师方法风格生成\n"
            "4. 提供快速复习要点和时间分配建议"
        ),
        preferred_model="deepseek",
        default_agent_type="subject",
    ),
}


def get_scene_preset(scene_type: str) -> ScenePreset | None:
    """获取场景预设配置

    Args:
        scene_type: 场景类型标识

    Returns:
        ScenePreset 或 None（场景不存在时）
    """
    return SCENE_PRESETS.get(scene_type)


def get_all_scene_types() -> list[str]:
    """获取所有场景类型列表"""
    return list(SCENE_PRESETS.keys())
