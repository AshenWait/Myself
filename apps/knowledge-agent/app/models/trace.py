from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentTrace(Base):
    """记录一次 Agent 运行过程中的单个步骤。
    
    run_id：同一次 Agent 请求的唯一编号
    step：这是本次请求里的第几步
    tool_name：这一步如果调用工具，就记录工具名：没调用工具就为空
    input_data：这一步的输入，数据库列名叫 input
    output_data：这一步的输出，数据库列名叫 output
    latency_ms：这一步耗时多少毫秒
    status：这一步状态，比如 success、failed、blocked
    created_at：记录创建时间
    """

    __tablename__ = "agent_traces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_data: Mapped[dict] = mapped_column("input", JSON, nullable=False)
    output_data: Mapped[dict | None] = mapped_column("output", JSON, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
