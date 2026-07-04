import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.guardrail import InputRiskLog

#该装饰器可省略__init__()
@dataclass(frozen=True)
class InputGuardrailResult:
    """输入检查结果。"""

    allowed: bool #是否通过 
    risk_level: str #风险等级
    reasons: list[str] #原因


PROMPT_INJECTION_PATTERNS = [
    r"忽略.*(之前|以上|所有).*指令",
    r"忽略.*系统.*规则",
    r"不要遵守.*规则",
    r"显示.*系统提示词",
    r"泄露.*系统提示词",
    r"ignore .*previous .*instructions",
    r"ignore .*system .*prompt",
    r"reveal .*system .*prompt",
]


def check_user_input(message: str) -> InputGuardrailResult:
    """检查用户输入是否包含明显 prompt injection。"""

    clean_message = message.strip()
    reasons = []

    if len(clean_message) > 4000:
        reasons.append("输入过长，可能试图塞入异常上下文。")

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, clean_message, flags=re.IGNORECASE):#正则表达式的标志参数，匹配时忽略大小写
            reasons.append(f"命中风险模式：{pattern}")

    if reasons:
        return InputGuardrailResult(
            allowed=False,
            risk_level="high",
            reasons=reasons,
        )

    return InputGuardrailResult(
        allowed=True,
        risk_level="low",
        reasons=[],
    )


def log_risk_input(
    db: Session | None,
    message: str,
    result: InputGuardrailResult,
) -> InputRiskLog | None:
    """把风险输入写入数据库；测试场景 db=None 时跳过写入。"""
    
    #测试场景跳过数据库写入
    if db is None: 
        return None

    #创建日志记录
    log = InputRiskLog(
        message=message,
        risk_level=result.risk_level,
        reasons=result.reasons,
    )
    #写入数据库
    db.add(log)
    db.commit()
    db.refresh(log)

    return log
