from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.trace import TraceStepResponse, TraceStatsResponse
from app.services.trace import list_traces_by_run_id, trace_to_response, calculate_trace_stats


router = APIRouter(prefix="/api/traces", tags=["traces"])

@router.get("/stats", response_model=TraceStatsResponse)
def get_trace_stats(db: Session = Depends(get_db)) -> dict:
    """返回所有 trace 的汇总统计。"""

    return calculate_trace_stats(db)

@router.get("/{run_id}", response_model=list[TraceStepResponse])
def get_trace_steps(run_id: str, db: Session = Depends(get_db)) -> list[dict]:
    """按 run_id 返回一次 Agent/RAG 运行的 trace 步骤。"""

    traces = list_traces_by_run_id(db, run_id)
    if not traces:
        raise HTTPException(status_code=404, detail="trace 不存在")

    return [trace_to_response(trace) for trace in traces]
