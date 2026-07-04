from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """聊天接口请求体，包含用户消息、可选文档范围和可选会话 id。"""
    message: str
    document_id: int | None = None
    session_id: int | None = None


class ChatSource(BaseModel):
    """聊天回答引用来源，描述命中的文档 chunk 和相似度距离。"""
    chunk_id: int
    document_id: int
    document_filename: str
    page_number: int
    chunk_index: int
    content: str
    distance: float


class ChatResponse(BaseModel):
    """普通聊天接口响应体，包含回答、消息 id、耗时和引用来源。"""
    reply: str
    session_id: int
    user_message_id: int
    assistant_message_id: int
    latency_ms: int
    sources: list[ChatSource]
    run_id: str | None = None

class ChatSessionResponse(BaseModel):
    """聊天会话列表响应体。"""
    id: int
    title: str
    created_at: datetime


class ChatMessageResponse(BaseModel):
    """聊天消息历史响应体。"""
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

class RagCallLogResponse(BaseModel):
    """RAG 调用日志响应体，展示一次问答背后的检索过程。"""
    id: int
    session_id: int
    question: str
    answer: str
    latency_ms: int
    retrieved_chunks: list[dict]
    created_at: datetime
