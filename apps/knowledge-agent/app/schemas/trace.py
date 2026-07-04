from datetime import datetime

from pydantic import BaseModel


class TraceStepResponse(BaseModel):
    """单条 trace 步骤响应。"""

    id: int
    run_id: str
    step: int
    tool_name: str | None
    input: dict
    output: dict | None
    latency_ms: float
    status: str
    created_at: datetime

class TraceStatsResponse(BaseModel):
    """Trace 汇总统计响应。"""

    total_runs: int
    total_steps: int
    failed_runs: int
    average_response_time_ms: float
    failure_rate: float
    average_tool_calls: float