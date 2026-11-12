"""
AI4Edu 诊断Agent
基于IRT模型分析知识掌握度，生成个性化诊断报告
使用简化2PL模型（Two-Parameter Logistic）
"""
import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


# IRT 2PL模型参数预设
# difficulty (b): 难度参数，范围[-3, 3]
# discrimination (a): 区分度参数，范围[0.5, 2.5]
IRT_PARAMS: Dict[str, Dict[str, float]] = {
    "easy": {"a": 1.0, "b": -1.0},
    "medium": {"a": 1.2, "b": 0.0},
    "hard": {"a": 1.5, "b": 1.0},
}


def irt_probability(theta: float, a: float, b: float, c: float = 0.25) -> float:
    """
    IRT 3PL模型概率计算（简化为2PL，c=0.25用于选择题猜测参数）

    P(θ) = c + (1 - c) / (1 + exp(-a * (θ - b)))

    Args:
        theta: 被试能力参数
        a: 区分度
        b: 难度
        c: 猜测参数（选择题默认0.25）

    Returns:
        答对概率 [0, 1]
    """
    exponent = -a * (theta - b)
    # 防止溢出
    exponent = max(-30.0, min(30.0, exponent))
    probability = c + (1 - c) / (1 + math.exp(exponent))
    return probability


def estimate_theta_mle(
    responses: List[Dict[str, Any]],
    initial_theta: float = 0.0,
    max_iterations: int = 50,
    convergence: float = 0.001,
) -> float:
    """
    使用最大似然估计（MLE）估算被试能力θ

    Args:
        responses: 答题记录列表，每条包含 {is_correct, difficulty, discrimination}
        initial_theta: 初始θ值
        max_iterations: 最大迭代次数
        convergence: 收敛阈值

    Returns:
        估算的能力值θ
    """
    theta = initial_theta

    for _ in range(max_iterations):
        first_derivative = 0.0
        second_derivative = 0.0

        for resp in responses:
            is_correct = resp.get("is_correct", False)
            a = resp.get("discrimination", 1.0)
            b = resp.get("difficulty_b", 0.0)
            c = resp.get("guessing", 0.25)

            p = irt_probability(theta, a, b, c)
            p = max(0.001, min(0.999, p))  # 避免除零

            # 一阶导数
            q = 1 - p
            first_derivative += a * (is_correct - p) * (p - c) / (p * q)

            # 二阶导数
            w = (p - c) / p
            second_derivative -= a * a * w * w * q / p

        if abs(second_derivative) < 1e-10:
            break

        delta = first_derivative / abs(second_derivative)
        delta = max(-1.0, min(1.0, delta))  # 限制步长
        theta += delta

        if abs(delta) < convergence:
            break

    # 限制θ在合理范围
    return max(-4.0, min(4.0, theta))


class DiagnosisAgent(BaseAgent):
    """诊断Agent"""

    agent_type: str = "diagnosis"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的诊断分析专家。你基于IRT（项目反应理论）模型"
            "分析学生的知识掌握情况，生成个性化诊断报告。\n\n"
            "诊断报告要求：\n"
            "1. 按知识点维度分析掌握程度\n"
            "2. 区分知识盲区和概念误区\n"
            "3. 给出针对性的学习建议\n"
            "4. 推荐学习路径和资源\n"
            "5. 使用可视化友好的结构（Markdown）呈现\n"
            "6. 能力值θ的范围及含义：θ<-1为较弱，-1≤θ<0为一般，0≤θ<1为良好，θ≥1为优秀"
        )

    async def generate_diagnosis_report(
        self,
        diagnosis_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成诊断报告

        Args:
            diagnosis_data: 诊断数据，包含答题记录、知识点等
            context: 上下文信息

        Returns:
            诊断报告
        """
        questions = diagnosis_data.get("questions", [])
        user_answers = diagnosis_data.get("user_answers", {})

        # 1. IRT能力估算
        responses = self._prepare_irt_responses(questions, user_answers)
        theta = estimate_theta_mle(responses)

        # 2. 知识点维度分析
        knowledge_analysis = self._analyze_knowledge_dimensions(questions, user_answers)

        # 3. 生成文字报告
        report = await self._generate_text_report(theta, knowledge_analysis, context)

        return {
            "theta": round(theta, 3),
            "theta_level": self._theta_to_level(theta),
            "total_questions": len(questions),
            "correct_count": sum(1 for r in responses if r.get("is_correct")),
            "accuracy": round(
                sum(1 for r in responses if r.get("is_correct")) / max(len(responses), 1) * 100, 1
            ),
            "knowledge_analysis": knowledge_analysis,
            "report": report,
        }

    def _prepare_irt_responses(
        self,
        questions: List[Dict[str, Any]],
        user_answers: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        准备IRT计算所需的答题数据

        Args:
            questions: 题目列表
            user_answers: 用户答案映射

        Returns:
            IRT格式的答题记录
        """
        responses: List[Dict[str, Any]] = []
        for q in questions:
            q_id = str(q.get("id", ""))
            difficulty = q.get("difficulty", "medium")
            irt_param = IRT_PARAMS.get(difficulty, IRT_PARAMS["medium"])

            user_ans = user_answers.get(q_id, "")
            correct_ans = q.get("correct_answer", "")
            is_correct = user_ans.strip().lower() == correct_ans.strip().lower()

            responses.append({
                "is_correct": is_correct,
                "difficulty": difficulty,
                "difficulty_b": irt_param["b"],
                "discrimination": irt_param["a"],
                "guessing": 0.25 if q.get("question_type") == "choice" else 0.0,
                "knowledge_points": q.get("knowledge_points", []),
            })

        return responses

    def _analyze_knowledge_dimensions(
        self,
        questions: List[Dict[str, Any]],
        user_answers: Dict[str, str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        按知识点维度分析掌握情况

        Args:
            questions: 题目列表
            user_answers: 用户答案映射

        Returns:
            知识点维度的掌握分析
        """
        kp_stats: Dict[str, Dict[str, Any]] = {}

        for q in questions:
            q_id = str(q.get("id", ""))
            user_ans = user_answers.get(q_id, "")
            correct_ans = q.get("correct_answer", "")
            is_correct = user_ans.strip().lower() == correct_ans.strip().lower()

            knowledge_points = q.get("knowledge_points", [])
            if isinstance(knowledge_points, str):
                try:
                    knowledge_points = json.loads(knowledge_points)
                except (json.JSONDecodeError, TypeError):
                    knowledge_points = [knowledge_points]

            for kp in knowledge_points:
                if kp not in kp_stats:
                    kp_stats[kp] = {"total": 0, "correct": 0}
                kp_stats[kp]["total"] += 1
                if is_correct:
                    kp_stats[kp]["correct"] += 1

        # 计算每个知识点的掌握率
        result: Dict[str, Dict[str, Any]] = {}
        for kp, stats in kp_stats.items():
            accuracy = stats["correct"] / max(stats["total"], 1) * 100
            if accuracy >= 80:
                level = "掌握良好"
            elif accuracy >= 60:
                level = "基本掌握"
            elif accuracy >= 40:
                level = "有待提高"
            else:
                level = "薄弱知识点"
            result[kp] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": round(accuracy, 1),
                "level": level,
            }

        return result

    def _theta_to_level(self, theta: float) -> str:
        """将θ值转换为等级描述"""
        if theta < -1:
            return "较弱"
        elif theta < 0:
            return "一般"
        elif theta < 1:
            return "良好"
        else:
            return "优秀"

    async def _generate_text_report(
        self,
        theta: float,
        knowledge_analysis: Dict[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成文字诊断报告"""
        # 构建输入给LLM的消息
        strengths = [kp for kp, v in knowledge_analysis.items() if v["accuracy"] >= 80]
        weaknesses = [kp for kp, v in knowledge_analysis.items() if v["accuracy"] < 60]

        analysis_text = (
            f"能力值θ：{theta:.3f}（{self._theta_to_level(theta)}）\n\n"
            f"知识点掌握情况：\n"
        )
        for kp, v in knowledge_analysis.items():
            analysis_text += f"- {kp}: 正确率{v['accuracy']}%，{v['level']}\n"
        if strengths:
            analysis_text += f"\n优势知识点：{', '.join(strengths)}\n"
        if weaknesses:
            analysis_text += f"\n薄弱知识点：{', '.join(weaknesses)}\n"

        messages = [
            {
                "role": "user",
                "content": (
                    f"请根据以下诊断数据生成详细的个性化诊断报告，"
                    f"包含总体评价、知识分析、学习建议三部分：\n\n{analysis_text}"
                ),
            }
        ]

        result = await super().execute(messages, context)
        return result.get("content", "")
