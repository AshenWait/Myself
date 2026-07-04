import json

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.services.agent import AgentService
from app.services.output_guardrails import check_answer_output
from app.services.trace import TraceRecorder, calculate_trace_stats


class MemoryTraceRecorder(TraceRecorder):
    """在内存里保存 trace，方便排查练习不依赖真实数据库。"""

    def __init__(self):
        super().__init__(db=None)
        self.records = []

    def record(self, *, tool_name, input_data, output_data, latency_ms, status):
        self.records.append(
            {
                "tool_name": tool_name,
                "input_data": input_data,
                "output_data": output_data,
                "latency_ms": latency_ms,
                "status": status,
            }
        )
        return None


def parse_tool_decision(raw_text: str) -> dict:
    """模拟把模型输出解析成工具决策，用来制造格式错误场景。"""

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"模型返回不是合法 JSON：{exc}"}

    if not isinstance(data, dict):
        return {"ok": False, "error": "模型返回 JSON 不是对象"}

    if "tool_name" not in data or "arguments" not in data:
        return {"ok": False, "error": "模型返回缺少 tool_name 或 arguments"}

    if not isinstance(data["arguments"], dict):
        return {"ok": False, "error": "arguments 必须是对象"}

    return {"ok": True, "data": data}


def case_retrieval_miss() -> None:
    recorder = MemoryTraceRecorder()
    recorder.record(
        tool_name="retrieve_documents",
        input_data={"type": "tool_call", "arguments": {"query": "火星基地预算"}},
        output_data={"type": "list", "count": 0, "preview": []},
        latency_ms=12.5,
        status="success",
    )

    record = recorder.records[0]
    assert record["status"] == "success"
    assert record["output_data"]["count"] == 0
    print("Case 1 检索不到资料：工具成功执行，但返回 0 条结果。")


def case_tool_error() -> None:
    recorder = MemoryTraceRecorder()
    agent = AgentService(db=None, trace_recorder=recorder)

    try:
        agent._run_tool("retrieve_documents", {"query": "", "limit": 3})
    except ValidationError:
        pass
    else:
        raise AssertionError("空 query 应该触发参数校验错误")

    record = recorder.records[0]
    assert record["tool_name"] == "retrieve_documents"
    assert record["status"] == "failed"
    assert "error" in record["output_data"]
    print("Case 2 工具调用报错：参数校验失败，并写入 failed trace。")


def case_model_format_error() -> None:
    recorder = MemoryTraceRecorder()
    raw_output = "我觉得应该调用检索工具，但我没有返回 JSON。"
    parsed = parse_tool_decision(raw_output)

    recorder.record(
        tool_name=None,
        input_data={"type": "tool_decision", "raw_output": raw_output},
        output_data=parsed,
        latency_ms=3.2,
        status="failed",
    )

    assert parsed["ok"] is False
    assert recorder.records[0]["status"] == "failed"
    print("Case 3 模型格式错：模型输出不能被解析成工具决策。")


def case_missing_citation() -> None:
    result = check_answer_output(
        answer="这个项目一定已经上线生产环境。",
        sources=[],
    )

    assert result.allowed is False
    assert result.risk_level == "high"
    print("Case 4 引用缺失：无来源的确定性回答被输出检查拦截。")


def case_slow_request() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    recorder = TraceRecorder(db=db, run_id="run-slow")
    recorder.record(
        tool_name=None,
        input_data={"type": "llm_call", "model": "fake-model"},
        output_data={"answer_preview": "慢请求模拟"},
        latency_ms=3500,
        status="success",
    )

    stats = calculate_trace_stats(db)
    assert stats["total_runs"] == 1
    assert stats["average_response_time_ms"] == 3500.0

    db.close()
    print("Case 5 响应过慢：trace latency_ms 能定位慢步骤。")


def main() -> None:
    case_retrieval_miss()
    case_tool_error()
    case_model_format_error()
    case_missing_citation()
    case_slow_request()
    print("Day 55 五类排查场景检查通过。")


if __name__ == "__main__":
    main()
