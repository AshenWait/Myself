from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.services.agent as agent_module
from app.models.base import Base
from app.services.agent import AgentService
from app.services.trace import (
    TraceRecorder,
    list_traces_by_run_id,
    summarize_for_trace,
)


class MemoryTraceRecorder(TraceRecorder):
    def __init__(self):
        super().__init__(db=None)
        self.records = []

    def record(
        self,
        *,
        tool_name,
        input_data,
        output_data,
        latency_ms,
        status,
    ):
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


def check_database_trace_query() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    recorder = TraceRecorder(db=db, run_id="run-test")

    recorder.record(
        tool_name="retrieve_documents",
        input_data={"type": "tool_call", "arguments": {"query": "文档"}},
        output_data={"type": "list", "count": 0, "preview": []},
        latency_ms=12.3,
        status="success",
    )
    recorder.record(
        tool_name="create_note",
        input_data={"type": "tool_call", "arguments": {"title": "测试"}},
        output_data={"error": "需要用户确认"},
        latency_ms=1.2,
        status="blocked",
    )

    traces = list_traces_by_run_id(db, "run-test")

    assert len(traces) == 2
    assert [trace.step for trace in traces] == [1, 2]
    assert traces[0].tool_name == "retrieve_documents"
    assert traces[1].status == "blocked"

    db.close()


def check_agent_tool_success_trace() -> None:
    original_list_documents = agent_module.list_documents

    def fake_list_documents(db):
        return [
            {
                "document_id": 1,
                "filename": "sample.txt",
                "content_type": "text/plain",
                "page_count": 1,
                "created_at": None,
            }
        ]

    agent_module.list_documents = fake_list_documents

    try:
        recorder = MemoryTraceRecorder()
        agent = AgentService(db=None, trace_recorder=recorder)

        result = agent._run_tool("list_documents", {})

        assert result[0]["filename"] == "sample.txt"
        assert len(recorder.records) == 1

        record = recorder.records[0]
        assert record["tool_name"] == "list_documents"
        assert record["status"] == "success"
        assert record["input_data"]["type"] == "tool_call"
        assert record["output_data"]["type"] == "list"
        assert record["output_data"]["count"] == 1
    finally:
        agent_module.list_documents = original_list_documents


def check_agent_tool_blocked_trace() -> None:
    recorder = MemoryTraceRecorder()
    agent = AgentService(
        db=None,
        trace_recorder=recorder,
        allowed_tools={"list_documents"},
    )

    try:
        agent._run_tool("retrieve_documents", {"query": "文档", "limit": 3})
    except PermissionError:
        pass
    else:
        raise AssertionError("retrieve_documents 不在白名单中，不应该执行")

    assert len(recorder.records) == 1
    record = recorder.records[0]
    assert record["tool_name"] == "retrieve_documents"
    assert record["status"] == "blocked"
    assert "error" in record["output_data"]


def main() -> None:
    assert summarize_for_trace(None)["type"] == "none"
    assert summarize_for_trace([1, 2, 3, 4])["count"] == 4
    assert summarize_for_trace({"a": 1})["keys"] == ["a"]

    check_database_trace_query()
    check_agent_tool_success_trace()
    check_agent_tool_blocked_trace()

    print("Day 52 工具调用 Trace 检查通过。")


if __name__ == "__main__":
    main()
