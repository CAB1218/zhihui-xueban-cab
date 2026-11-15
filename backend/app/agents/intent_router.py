"""
智慧学伴 意图路由
根据用户输入的关键词和规则，将请求分类到具体Agent
9种意图：知识问答、作业辅导、测验出题、文件解析、备课、学伴、诊断、课堂管理、心理支持 + fallback通用
"""
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """意图类型枚举"""

    RAG = "rag"                         # 知识问答
    SUBJECT = "subject"                 # 学科专家/作业辅导
    QUIZ = "quiz"                       # 测验出题
    FILE_RAG = "file_rag"               # 文件解析
    LESSON_PLAN = "lesson_plan"          # 备课
    BUDDY = "buddy"                     # 学伴
    DIAGNOSIS = "diagnosis"             # 诊断
    CLASSROOM = "classroom"             # 课堂管理
    PSYCHOLOGY = "psychology"           # 心理支持
    ANTI_MISCONCEPTION = "anti_misconception"  # 反misconception
    GENERAL = "general"                 # 通用fallback


# 意图关键词规则表（按优先级排列，优先匹配的排前面）
INTENT_RULES: List[Dict[str, Any]] = [
    {
        "intent": IntentType.QUIZ,
        "keywords": [
            "出题", "出一份题", "测试题", "考试题", "测验", "试题",
            "选择题", "填空题", "问答题", "练习题", "组卷",
            "考卷", "模拟考试", "随堂测试", "单元测试",
        ],
        "patterns": [r"出.*题", r"生成.*测试", r"组.*卷"],
    },
    {
        "intent": IntentType.DIAGNOSIS,
        "keywords": [
            "诊断", "知识掌握", "薄弱点", "弱点分析", "评估水平",
            "学习诊断", "知识诊断", "能力评估", "水平测试",
            "知识点掌握", "掌握程度",
        ],
        "patterns": [r"诊断.*知识", r"分析.*薄弱", r"评估.*水平"],
    },
    {
        "intent": IntentType.PSYCHOLOGY,
        "keywords": [
            "焦虑", "压力", "心情", "紧张", "失眠", "烦躁",
            "不想学", "厌学", "情绪", "心理", "抑郁", "烦躁",
            "不开心", "难受", "疲惫", "身心",
        ],
        "patterns": [r"心情.*不好", r"压力.*大", r"不想.*学"],
    },
    {
        "intent": IntentType.LESSON_PLAN,
        "keywords": [
            "备课", "教案", "教学计划", "课程设计", "教学目标",
            "教学方案", "课时计划", "教学大纲", "备课方案",
        ],
        "patterns": [r"备.*课", r"设计.*教案", r"教学.*计划"],
    },
    {
        "intent": IntentType.CLASSROOM,
        "keywords": [
            "课堂", "点名", "签到", "举手", "投票", "弹幕",
            "课堂互动", "课堂管理", "发题", "抢答", "课堂活动",
        ],
        "patterns": [r"课堂.*互动", r"课堂.*管理"],
    },
    {
        "intent": IntentType.FILE_RAG,
        "keywords": [
            "上传文件", "解析文件", "PDF", "文档解析", "文件内容",
            "Word文档", "PPT内容", "文件问答", "阅读文件",
        ],
        "patterns": [r"解析.*文件", r"文件.*问答", r"上传.*文档"],
    },
    {
        "intent": IntentType.ANTI_MISCONCEPTION,
        "keywords": [
            "错误概念", "误解", "misconception", "常见错误",
            "易错点", "典型错误", "概念纠偏", "认知偏差",
            "常犯错误", "错解",
        ],
        "patterns": [r"常见.*错误", r"易错.*点", r"错误.*概念"],
    },
    {
        "intent": IntentType.BUDDY,
        "keywords": [
            "学伴", "陪我学", "学习伙伴", "聊天", "鼓励我",
            "无聊", "加油", "学不下去", "一起学", "打卡",
        ],
        "patterns": [r"陪我.*学", r"一起.*学", r"学不下去"],
    },
    {
        "intent": IntentType.SUBJECT,
        "keywords": [
            "数学题", "物理题", "化学题", "生物题", "历史题",
            "地理题", "语文题", "英语题", "编程题",
            "解题", "算数", "方程", "力学", "电路",
            "化学反应", "遗传", "光合作用", "牛顿",
        ],
        "patterns": [
            r"求解.*题", r"怎么做.*题", r"讲解.*原理",
            r"\d+\s*[\+\-\*\/\=]",  # 算术表达式
        ],
    },
    {
        "intent": IntentType.RAG,
        "keywords": [
            "什么是", "解释", "概念", "定义", "原理",
            "知识", "知识点", "讲解", "百科", "查一下",
            "告诉我", "介绍一下", "说明", "含义",
        ],
        "patterns": [r"什么是.*", r"解释.*概念", r"什么是.*原理"],
    },
]


class IntentRouter:
    """
    意图路由器

    使用关键词匹配 + 正则模式 + 优先级规则进行意图分类。
    保持轻量，不依赖ML模型。
    """

    def __init__(self) -> None:
        self.rules = INTENT_RULES

    def route(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentType:
        """
        根据用户输入进行意图分类

        Args:
            user_input: 用户输入文本
            context: 上下文信息（可用于辅助判断）

        Returns:
            识别出的意图类型
        """
        if not user_input or not user_input.strip():
            return IntentType.GENERAL

        text = user_input.strip().lower()

        # 1. 上下文暗示：如果当前场景/Agent类型已确定，优先沿用
        if context:
            scene_hint = self._get_context_hint(context)
            if scene_hint is not None:
                return scene_hint

        # 2. 按规则优先级依次匹配
        for rule in self.rules:
            intent = rule["intent"]

            # 关键词匹配
            for keyword in rule.get("keywords", []):
                if keyword.lower() in text:
                    logger.debug(
                        "intent_matched_by_keyword",
                        intent=intent.value,
                        keyword=keyword,
                    )
                    return intent

            # 正则模式匹配
            for pattern in rule.get("patterns", []):
                try:
                    if re.search(pattern, text):
                        logger.debug(
                            "intent_matched_by_pattern",
                            intent=intent.value,
                            pattern=pattern,
                        )
                        return intent
                except re.error:
                    continue

        # 3. 无匹配时，如果包含问号则默认为知识问答
        if "？" in text or "?" in text:
            return IntentType.RAG

        # 4. fallback 通用
        return IntentType.GENERAL

    def _get_context_hint(self, context: Dict[str, Any]) -> Optional[IntentType]:
        """
        根据上下文暗示判断意图

        Args:
            context: 上下文信息

        Returns:
            暗示的意图类型或None
        """
        # 如果当前已在某个Agent会话中，优先沿用
        current_agent = context.get("current_agent_type", "")
        agent_to_intent = {
            "rag": IntentType.RAG,
            "subject": IntentType.SUBJECT,
            "quiz": IntentType.QUIZ,
            "file_rag": IntentType.FILE_RAG,
            "lesson_plan": IntentType.LESSON_PLAN,
            "buddy": IntentType.BUDDY,
            "diagnosis": IntentType.DIAGNOSIS,
            "classroom": IntentType.CLASSROOM,
            "psychology": IntentType.PSYCHOLOGY,
            "anti_misconception": IntentType.ANTI_MISCONCEPTION,
            "general": IntentType.GENERAL,
        }
        if current_agent in agent_to_intent:
            return agent_to_intent[current_agent]

        # 场景暗示
        scene_type = context.get("scene_type", "")
        scene_to_intent = {
            "classroom": IntentType.CLASSROOM,
            "study": IntentType.RAG,
            "exam": IntentType.QUIZ,
        }
        if scene_type in scene_to_intent:
            return scene_to_intent[scene_type]

        return None

    def get_agent_type(self, intent: IntentType) -> str:
        """将意图类型映射为Agent类型字符串"""
        mapping = {
            IntentType.RAG: "rag",
            IntentType.SUBJECT: "subject",
            IntentType.QUIZ: "quiz",
            IntentType.FILE_RAG: "file_rag",
            IntentType.LESSON_PLAN: "lesson_plan",
            IntentType.BUDDY: "buddy",
            IntentType.DIAGNOSIS: "diagnosis",
            IntentType.CLASSROOM: "classroom",
            IntentType.PSYCHOLOGY: "psychology",
            IntentType.ANTI_MISCONCEPTION: "anti_misconception",
            IntentType.GENERAL: "general",
        }
        return mapping.get(intent, "general")


# 全局单例
intent_router = IntentRouter()
