"""
AI4Edu 反Misconception Agent
识别常见错误概念并提供纠正
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


# 常见misconception知识库（规则引擎，非ML）
COMMON_MISCONCEPTIONS: List[Dict[str, Any]] = [
    {
        "subject": "physics",
        "topic": "牛顿运动定律",
        "misconception": "重的物体比轻的物体下落快",
        "correction": "在真空中（忽略空气阻力），所有物体下落加速度相同，与质量无关。伽利略的比萨斜塔实验证明了这一点。",
        "keywords": ["重的下落快", "质量大落得快", "重力大下落快"],
    },
    {
        "subject": "physics",
        "topic": "力与运动",
        "misconception": "有力才有运动，没有力就停止",
        "correction": "根据牛顿第一定律，力是改变运动状态的原因，而非维持运动的原因。没有外力作用时，物体会保持匀速直线运动或静止。",
        "keywords": ["没有力就停", "力维持运动", "没力不动"],
    },
    {
        "subject": "physics",
        "topic": "电流",
        "misconception": "电流从正极流向负极，所以正极的电先到",
        "correction": "电流是电场传播，速度接近光速，不是电子本身的运动速度。电子漂移速度实际上很慢，但电场瞬间建立。",
        "keywords": ["电先到", "正极先到", "电流速度"],
    },
    {
        "subject": "chemistry",
        "topic": "化学平衡",
        "misconception": "化学平衡时反应停止了",
        "correction": "化学平衡是动态平衡，正反应和逆反应仍在进行，只是速率相等，宏观上浓度不变。",
        "keywords": ["平衡就停", "反应停止", "不再反应"],
    },
    {
        "subject": "chemistry",
        "topic": "燃烧",
        "misconception": "燃烧必须有氧气参与",
        "correction": "燃烧是剧烈的氧化反应，不一定需要氧气。例如钠在氯气中燃烧、镁在二氧化碳中燃烧。",
        "keywords": ["燃烧需要氧气", "没氧不能烧", "氧气才能燃烧"],
    },
    {
        "subject": "math",
        "topic": "函数",
        "misconception": "函数必须有解析表达式",
        "correction": "函数的本质是对应关系，只要满足一一对应或多一对应即可，不需要有解析表达式。例如狄利克雷函数。",
        "keywords": ["函数有公式", "没有公式不是函数"],
    },
    {
        "subject": "math",
        "topic": "无穷",
        "misconception": "0.999...不等于1",
        "correction": "0.999...（无限循环）严格等于1。可以用多种方法证明，如1/3=0.333...，3×(1/3)=1=3×0.333...=0.999...",
        "keywords": ["0.999不等于1", "0.9循环不是1"],
    },
    {
        "subject": "biology",
        "topic": "进化",
        "misconception": "进化是有方向、有目的的过程",
        "correction": "进化没有预定的方向和目的，是随机突变加上自然选择的结果。适应环境是结果而非原因。",
        "keywords": ["进化方向", "进化目的", "越来越高级"],
    },
    {
        "subject": "biology",
        "topic": "呼吸",
        "misconception": "植物白天光合作用，晚上才呼吸",
        "correction": "植物全天都在进行呼吸作用。白天光合作用强度大于呼吸作用，净效果是吸收CO2释放O2。",
        "keywords": ["植物晚上呼吸", "白天不呼吸", "白天只光合"],
    },
    {
        "subject": "geography",
        "topic": "季节",
        "misconception": "夏天热是因为地球离太阳近",
        "correction": "季节变化是因为地轴倾斜导致太阳直射点移动，与日地距离无关。事实上北半球夏天时地球反而离太阳更远。",
        "keywords": ["夏天离太阳近", "近所以热", "远所以冷"],
    },
]


class AntiMisconceptionAgent(BaseAgent):
    """反Misconception Agent"""

    agent_type: str = "anti_misconception"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的反错误概念专家。你的任务是识别学生常见的错误概念"
            "（misconception），并提供准确的纠正和深入解释。\n\n"
            "工作方式：\n"
            "1. 仔细分析学生的表述，识别可能存在的错误概念\n"
            "2. 明确指出错误概念是什么\n"
            "3. 用通俗易懂的语言解释为什么这是错的\n"
            "4. 提供正确的理解和解释\n"
            "5. 给出相关的实验、例子或证明来加强理解\n"
            "6. 提供类似的常见错误概念作为拓展\n"
            "7. 态度温和，不嘲笑学生的错误理解\n"
            "8. 鼓励学生提出疑问，加深理解"
        )

    def detect_misconceptions(self, user_input: str) -> List[Dict[str, Any]]:
        """
        检测用户输入中的常见错误概念

        Args:
            user_input: 用户输入文本

        Returns:
            匹配到的错误概念列表
        """
        detected: List[Dict[str, Any]] = []
        text_lower = user_input.lower()

        for mc in COMMON_MISCONCEPTIONS:
            for keyword in mc.get("keywords", []):
                if keyword.lower() in text_lower:
                    detected.append(mc)
                    break

        return detected

    def suggest_for_node(
        self,
        name: str,
        description: str,
        subject: str,
    ) -> List[Dict[str, Any]]:
        """
        基于节点名称和描述，匹配 COMMON_MISCONCEPTIONS 规则库，
        返回 AI 标注建议列表（含置信度）

        Args:
            name: 知识节点名称
            description: 知识节点描述
            subject: 知识节点所属学科（英文 ID）

        Returns:
            匹配到的 misconception 建议列表，每项包含 confidence 字段
        """
        suggestions: List[Dict[str, Any]] = []
        combined_text = f"{name} {description}".lower()

        for mc in COMMON_MISCONCEPTIONS:
            # 先按 subject 过滤
            if mc.get("subject", "").lower() != subject.lower():
                continue

            keywords = mc.get("keywords", [])
            if not keywords:
                continue

            # 统计匹配到的关键词数
            matched_keywords = [
                kw for kw in keywords if kw.lower() in combined_text
            ]

            # 也检查 topic 是否出现在 name 中
            topic = mc.get("topic", "")
            topic_matched = topic and topic in name

            if not matched_keywords and not topic_matched:
                continue

            # 计算置信度 = 匹配关键词数 / 总关键词数
            confidence = len(matched_keywords) / len(keywords) if keywords else 0.0

            # 如果 topic 也匹配，增加置信度
            if topic_matched:
                confidence = min(confidence + 0.2, 1.0)

            # 低于 0.5 置信度不展示
            if confidence < 0.5:
                continue

            suggestions.append({
                "misconception": mc.get("misconception", ""),
                "correction": mc.get("correction", ""),
                "topic": topic,
                "keywords": keywords,
                "subject": mc.get("subject", subject),
                "confidence": round(confidence, 2),
            })

        return suggestions

    async def execute(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行反misconception分析"""
        # 提取用户消息
        user_input = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_input = msg.get("content", "")
                break

        # 先做规则匹配
        detected = self.detect_misconceptions(user_input)

        # 如果有匹配的misconception，注入到上下文中
        if detected:
            mc_context = "【检测到以下常见错误概念】\n"
            for i, mc in enumerate(detected, 1):
                mc_context += (
                    f"{i}. 主题：{mc['topic']}\n"
                    f"   错误概念：{mc['misconception']}\n"
                    f"   正确理解：{mc['correction']}\n\n"
                )
            mc_context += "请基于以上信息，温和地纠正学生的错误概念，并提供深入的解释。"

            augmented = list(messages)
            augmented.insert(
                -1,
                {"role": "system", "content": mc_context},
            )
            result = await super().execute(augmented, context)
        else:
            result = await super().execute(messages, context)

        result["detected_misconceptions"] = len(detected)
        return result
