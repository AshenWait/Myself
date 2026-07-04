from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.trace import AgentTrace


@dataclass
class TraceRecorder:
    """负责把 Agent 运行步骤写入 agent_traces 表。"""

    db: Session | None
    run_id: str = field(default_factory=lambda: uuid4().hex)#标识一次完整的 Agent 运行，同一 run 的所有步骤共享此 ID
    step: int = 0 #当前步骤计数器，每次 record 自动 +1

    def next_step(self) -> int:
        """生成当前 run 的下一步编号。"""

        self.step += 1
        return self.step

    def record(
        self,
        *,
        tool_name: str | None,
        input_data: dict,
        output_data: dict | None,
        latency_ms: float,
        status: str, #状态标识，如 "success"、"error"、"pending"
    ) -> AgentTrace | None:
        """写入一条 trace；测试场景 db=None 时跳过数据库写入。"""

        if self.db is None:
            return None

        trace = AgentTrace(
            run_id=self.run_id,
            step=self.next_step(),
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
            latency_ms=latency_ms,
            status=status,
        )

        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)

        return trace


def now_ms() -> float:
    """返回当前时间，单位是毫秒。"""

    return time.perf_counter() * 1000


def elapsed_ms(start_ms: float) -> float:
    """根据开始时间计算耗时，单位是毫秒。"""

    return time.perf_counter() * 1000 - start_ms


def preview_text(text: str, max_length: int = 200) -> str:
    """生成适合写入日志的文本预览，避免把完整 prompt 全塞进 trace。"""

    clean_text = text.replace("\n", " ").strip()
    if len(clean_text) <= max_length:
        return clean_text
    return clean_text[:max_length] + "..."

def summarize_for_trace(value: Any, max_length: int = 500) -> dict:
    """把工具返回值压缩成适合写入 trace 的摘要。"""

    if value is None:
        return {"type": "none", "preview": None}
    if isinstance(value, list):#isinstance（）判断目标是什么类型
        return {
            "type": "list",
            "count": len(value),
            "preview": value[:3],
        }
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": list(value.keys()),
            "preview": value,
        }
    return {
        "type": type(value).__name__,
        "preview": preview_text(str(value), max_length=max_length),
    }

def list_traces_by_run_id(db: Session, run_id: str) -> list[AgentTrace]:
    """按 run_id 查询一次 Agent 运行的所有 trace。"""

    return (
        db.query(AgentTrace)
        .filter(AgentTrace.run_id == run_id)
        .order_by(AgentTrace.step)
        .all()
    )

def compact_trace_payload(value: Any, max_string_length: int = 200) -> Any:
    """压缩 trace 输入输出，避免前端展示过长原始参数。"""

    if value is None:
        return None

    if isinstance(value, str):
        return preview_text(value, max_length=max_string_length)

    if isinstance(value, list):
        return [compact_trace_payload(item, max_string_length) for item in value[:3]]

    if isinstance(value, dict):
        return {
            key: compact_trace_payload(item, max_string_length)
            for key, item in value.items()
        }

    return value


def trace_to_response(trace: AgentTrace) -> dict:
    """把数据库 trace 转成 API 响应字典。"""

    return {
        "id": trace.id,
        "run_id": trace.run_id,
        "step": trace.step,
        "tool_name": trace.tool_name,
        "input": compact_trace_payload(trace.input_data),
        "output": compact_trace_payload(trace.output_data),
        "latency_ms": trace.latency_ms,
        "status": trace.status,
        "created_at": trace.created_at,
    }

#只要某个 run 里面出现 failed 或 blocked，这次请求就算失败
FAILED_TRACE_STATUSES = {"failed", "blocked"}

def calculate_trace_stats(db: Session) -> dict:
    """统计 trace 的整体观测指标。

    这里按 run_id 分组：
    - 一组 run_id 代表一次完整请求
    - 每个 run 的响应时间 = 该 run 下所有 step 的 latency_ms 总和
    - 失败 run = 只要其中一步 failed 或 blocked，就算失败
    - 工具调用次数 = tool_name 不为空的 step 数量
    """

    traces = db.query(AgentTrace).all()

    if not traces:
        return {
            "total_runs": 0,
            "total_steps": 0,
            "failed_runs": 0,
            "average_response_time_ms": 0.0,
            "failure_rate": 0.0,
            "average_tool_calls": 0.0,
        }

    runs: dict[str, dict[str, Any]] = {}

    for trace in traces:
        run_info = runs.setdefault(#如果这个 run_id 第一次出现，就创建一个统计盒子。如果已经出现过，就继续拿之前那个盒子。
            trace.run_id,
            {
                "total_latency_ms": 0.0,
                "tool_calls": 0,
                "has_failure": False,
            },
        )

        run_info["total_latency_ms"] += float(trace.latency_ms or 0)

        if trace.tool_name is not None:
            run_info["tool_calls"] += 1

        if trace.status in FAILED_TRACE_STATUSES:
            run_info["has_failure"] = True

    total_runs = len(runs)
    failed_runs = sum(1 for run_info in runs.values() if run_info["has_failure"])
    #run的平均耗时
    average_response_time_ms = (
        sum(run_info["total_latency_ms"] for run_info in runs.values()) / total_runs
    )
    #run的失败率
    failure_rate = failed_runs / total_runs
    #所有工具调用次数 / run 数量
    average_tool_calls = (
        sum(run_info["tool_calls"] for run_info in runs.values()) / total_runs
    )

    return {
        "total_runs": total_runs,
        "total_steps": len(traces),
        "failed_runs": failed_runs,
        "average_response_time_ms": round(average_response_time_ms, 2),
        "failure_rate": round(failure_rate, 4),
        "average_tool_calls": round(average_tool_calls, 2),
    }
