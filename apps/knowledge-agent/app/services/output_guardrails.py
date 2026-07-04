from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.guardrail import OutputCheckLog


@dataclass(frozen=True)
class OutputGuardrailResult:
    """输出检查结果。"""

    allowed: bool
    risk_level: str
    reasons: list[str]

REFUSAL_PHRASES = [
    "没有找到足够信息",
    "没有检索到",
    "无法根据已上传文档回答",
]


def check_answer_output(
    answer: str,
    sources: list[dict], #检索到的知识库来源列表
) -> OutputGuardrailResult:
    """检查回答是否有来源支撑。"""

    clean_answer = answer.strip()
    reasons = []

    if not clean_answer:
        reasons.append("回答为空。")

    has_sources = len(sources) > 0 
    is_refusal = any(phrase in clean_answer for phrase in REFUSAL_PHRASES)#有True为True否则Flase

    if not has_sources and not is_refusal:
        reasons.append("回答没有引用来源，不能作为知识库答案返回。")

    if reasons:
        return OutputGuardrailResult(
            allowed=False,
            risk_level="high",
            reasons=reasons,
        )

    return OutputGuardrailResult(
        allowed=True,
        risk_level="low",
        reasons=[],
    )


def build_output_refusal(result: OutputGuardrailResult) -> str:
    """根据输出检查结果生成安全拒答。"""

    return "我不能在没有引用来源的情况下回答这个问题。请先上传相关文档，或换一个能在知识库中找到来源的问题。"


def log_output_check(
    db: Session | None,
    question: str,
    answer: str,
    result: OutputGuardrailResult,
) -> OutputCheckLog | None:
    """保存输出检查结果；测试场景 db=None 时跳过写入。"""

    if db is None:
        return None

    log = OutputCheckLog(
        question=question,
        answer=answer,
        allowed=result.allowed,
        risk_level=result.risk_level,
        reasons=result.reasons,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log
