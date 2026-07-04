from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.services.trace import TraceRecorder, calculate_trace_stats


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    success_run = TraceRecorder(db=db, run_id="run-success")
    success_run.record(
        tool_name=None,
        input_data={"type": "llm_call"},
        output_data={"answer_preview": "ok"},
        latency_ms=100,
        status="success",
    )
    success_run.record(
        tool_name="retrieve_documents",
        input_data={"type": "tool_call", "arguments": {"query": "文档"}},
        output_data={"type": "list", "count": 3},
        latency_ms=50,
        status="success",
    )

    failed_run = TraceRecorder(db=db, run_id="run-failed")
    failed_run.record(
        tool_name=None,
        input_data={"type": "llm_call"},
        output_data={"error": "模型调用失败"},
        latency_ms=200,
        status="failed",
    )

    stats = calculate_trace_stats(db)

    assert stats["total_runs"] == 2
    assert stats["total_steps"] == 3
    assert stats["failed_runs"] == 1
    assert stats["average_response_time_ms"] == 175.0
    assert stats["failure_rate"] == 0.5
    assert stats["average_tool_calls"] == 0.5

    print("Trace 统计结果:", stats)
    print("Day 54 Trace 统计检查通过。")

    db.close()


if __name__ == "__main__":
    main()
