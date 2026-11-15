"""
智慧学伴 学科专家Agent
提供数学/物理/化学/生物/历史/地理等学科专业解答
注入 ResourceContextBuilder 实现用户/课程级别的资源感知
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.agents.resource_context import resource_context_builder

logger = logging.getLogger(__name__)


# 学科专家提示词模板
SUBJECT_PROMPTS: Dict[str, str] = {
    "math": (
        "你是一位资深数学教育专家，擅长从初等数学到高等数学的全领域知识解答。\n"
        "回答要求：\n"
        "1. 解题步骤清晰，每步标注使用的定理或公式\n"
        "2. 复杂问题先给出思路，再逐步求解\n"
        "3. 适时给出多种解法对比\n"
        "4. 使用LaTeX公式排版（行内用$...$，独立行用$$...$$）\n"
        "5. 解完后总结关键知识点和易错点"
    ),
    "physics": (
        "你是一位物理学教授，精通力学、电磁学、热学、光学、量子物理等领域。\n"
        "回答要求：\n"
        "1. 先明确物理模型和适用条件\n"
        "2. 给出清晰的受力分析/电路图/光路图描述\n"
        "3. 使用国际单位制（SI）\n"
        "4. 公式推导完整，标注每个物理量的含义\n"
        "5. 联系实际生活中的物理现象进行类比"
    ),
    "chemistry": (
        "你是一位化学教育专家，擅长无机化学、有机化学、物理化学、分析化学等方向。\n"
        "回答要求：\n"
        "1. 化学方程式配平完整，标注反应条件\n"
        "2. 说明反应机理和电子转移过程\n"
        "3. 区分实验现象与本质原因\n"
        "4. 适当引入微观视角（分子、原子层面）解释\n"
        "5. 注意安全提示"
    ),
    "biology": (
        "你是一位生物学教授，精通细胞生物学、遗传学、生态学、分子生物学等方向。\n"
        "回答要求：\n"
        "1. 从分子机制到宏观现象多层面解释\n"
        "2. 结合实验证据和科学史\n"
        "3. 正确使用生物学专业术语\n"
        "4. 基因与表型的关系讲清楚\n"
        "5. 适当联系医学和健康知识"
    ),
    "history": (
        "你是一位历史学者，精通中国史和世界史，善于从多角度分析历史事件。\n"
        "回答要求：\n"
        "1. 史实准确，引用史料来源\n"
        "2. 从政治、经济、文化、社会等多维度分析\n"
        "3. 注重历史事件的因果关系和时代背景\n"
        "4. 培养历史思维和批判性思考\n"
        "5. 联系当代，体现历史启示"
    ),
    "geography": (
        "你是一位地理学教授，擅长自然地理、人文地理、区域地理等方向。\n"
        "回答要求：\n"
        "1. 空间思维，注重地理位置和分布规律\n"
        "2. 自然与人文因素综合分析\n"
        "3. 使用地图思维描述空间关系\n"
        "4. 关注人地关系和可持续发展\n"
        "5. 联系实际案例和时事"
    ),
    "chinese": (
        "你是一位语文教育专家，精通文学鉴赏、文言文解读、写作指导等方向。\n"
        "回答要求：\n"
        "1. 文学作品分析注重文本细读\n"
        "2. 文言文翻译准确，注意词类活用和特殊句式\n"
        "3. 写作指导从立意、结构、语言三方面入手\n"
        "4. 适当引用经典评论和名句\n"
        "5. 培养审美能力和文化素养"
    ),
    "english": (
        "你是一位英语教育专家，擅长语法讲解、阅读理解、写作技巧等方向。\n"
        "回答要求：\n"
        "1. 语法讲解用中文，例句中英对照\n"
        "2. 区分中式英语和地道表达\n"
        "3. 阅读理解先讲方法再讲内容\n"
        "4. 写作给出范文和修改建议\n"
        "5. 适当拓展文化背景知识"
    ),
    "cs": (
        "你是一位计算机科学教育专家，精通编程、算法、数据结构、操作系统等方向。\n"
        "回答要求：\n"
        "1. 代码示例使用标准语法，添加注释\n"
        "2. 算法讲解包含时间/空间复杂度分析\n"
        "3. 从问题出发，先讲思路再给实现\n"
        "4. 画图描述数据结构变化过程\n"
        "5. 补充工程实践中的注意事项"
    ),
}


class SubjectAgent(BaseAgent):
    """学科专家Agent"""

    agent_type: str = "subject"

    def __init__(self, subject: Optional[str] = None) -> None:
        """
        初始化学科专家

        Args:
            subject: 学科标识，如 math, physics, chemistry等
        """
        self._subject = subject or "math"

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def system_prompt(self) -> str:
        """根据学科返回对应的专业提示词"""
        prompt = SUBJECT_PROMPTS.get(
            self._subject,
            SUBJECT_PROMPTS["math"],
        )
        return (
            prompt
            + "\n\n回答语言为中文，专业术语附英文。"
            + "对于学生的问题，要有耐心，循循善诱。"
        )

    async def execute(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行学科问答

        在调用 LLM 前，通过 ResourceContextBuilder 构建用户学习资源上下文
        （笔记/资源/图谱/老师方法），注入到提示词中。
        """
        # 从上下文中获取学科信息
        if context and context.get("subject"):
            self._subject = context["subject"]

        # 构建 ResourceContext（笔记/资源/图谱/老师方法）
        if context and context.get("db") and context.get("user_id"):
            # 提取用户查询
            user_query = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_query = msg.get("content", "")
                    break

            try:
                context_result = await resource_context_builder.build(
                    db=context["db"],
                    user_id=context["user_id"],
                    tenant_id=context.get("tenant_id", 0),
                    course_id=context.get("course_id"),
                    query=user_query,
                    scene_type=context.get("scene_type"),
                )
                # 将资源上下文注入到 context 中
                if context_result.context_text:
                    context["resource_context"] = context_result.context_text
                # 将 citations 和 summary 透传到返回结果
                context["citations"] = resource_context_builder.citations_to_dicts(
                    context_result.citations
                )
                context["context_summary"] = context_result.summary
            except Exception as e:
                logger.error("SubjectAgent ResourceContext 构建失败: %s", e)

        return await super().execute(messages, context)

    async def stream_execute(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ):
        """流式学科问答"""
        if context and context.get("subject"):
            self._subject = context["subject"]
        async for chunk in super().stream_execute(messages, context):
            yield chunk
