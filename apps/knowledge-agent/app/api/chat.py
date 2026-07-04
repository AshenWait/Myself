from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.database import get_db
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    RagCallLogResponse,
)
from app.services.chat import ChatService

#前台接待员”：收请求、校验格式、调用 service

"""
prefix="/api"
设置路径前缀
这个路由器下的所有路由都会自动添加 /api前缀
比如：如果定义了路由 /messages，实际访问路径是 /api/messages
"""
router = APIRouter(prefix="/api", tags=["chat"])

#ChatRequest 是Pydantic 定义请求体结构，限制客户端必须传哪些字段，以及这些字段的类型。
#response_model 会告诉 FastAPI：这个接口应该返回什么结构；FastAPI 会据此生成文档、过滤多余字段，并在返回结构错误时抛出响应校验错误。
@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """处理普通 RAG 聊天：校验请求、检索资料、调用模型，并保存聊天与 RAG 日志。"""
    #拦截空消息
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    if len(request.message) > settings.max_chat_message_length:
        raise HTTPException(
            status_code=400,
            detail=f"消息不能超过 {settings.max_chat_message_length} 字",
        )

    service = ChatService(db)#创建业务对象
    #根据 id获取文档
    if request.document_id is not None:
        document = service.document_service.get_document(request.document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="文档不存在")
    #是否选定某会话
    if request.session_id is None:
        title = service.build_session_title(request.message)
        chat_session = service.create_session(title)#创建一条聊天会话
    else:
        chat_session = service.get_session(request.session_id)
        if chat_session is None:
            raise HTTPException(status_code=404, detail="聊天会话不存在")
    answer, latency, sources, run_id = service.chat(
        request.message,
        request.document_id,
        session_id=chat_session.id,
    )
    latency_ms = int(latency * 1000)
    user_message = service.add_message(chat_session.id,"user", request.message)#保存用户消息
    assistant_message = service.add_message(chat_session.id, "assistant", answer)#保存模型回答

    service.add_rag_log(
        session_id=chat_session.id,
        question=request.message,
        answer=answer,
        latency_ms=latency_ms,
        retrieved_chunks=sources,
    )

    return ChatResponse(
        reply=assistant_message.content,
        session_id=chat_session.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        latency_ms=latency_ms,
        sources=sources,
        run_id=run_id,
    )

@router.post("/chat/stream")
def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """处理流式 RAG 聊天：边接收模型输出边返回文本，并在结束后保存完整回答。"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    if len(request.message) > settings.max_chat_message_length:
        raise HTTPException(
            status_code=400,
            detail=f"消息不能超过 {settings.max_chat_message_length} 字",
        )

    service = ChatService(db)

    if request.session_id is None:
        title = service.build_session_title(request.message)
        chat_session = service.create_session(title)
    else:
        chat_session = service.get_session(request.session_id)
        if chat_session is None:
            raise HTTPException(status_code=404, detail="聊天会话不存在")

    chat_session_id = chat_session.id
    service.add_message(chat_session_id, "user", request.message)

    def generate():
        """生成流式响应内容，并把每段模型输出拼成最终答案保存。"""
        answer_parts = []

        query_embedding = service.embedding.embed_text(request.message)
        chunk_results = service.document_service.search_similar_chunks(
            query_embedding,
            limit=settings.rag_top_k,
            document_id=request.document_id,
        )

        relevant_results = [
            (chunk, distance)
            for chunk, distance in chunk_results
            if distance <= settings.max_rag_distance
        ]

        if not relevant_results:
            answer = "我在已上传文档里没有找到足够信息。"
            service.add_message(chat_session_id, "assistant", answer)
            yield answer
            return

        context = "\n\n".join(
            f"资料{index + 1}:\n{chunk.content}"
            for index, (chunk, distance) in enumerate(relevant_results)
        )

        prompt = f"""
你是 Knowledge Agent，请根据下面的资料回答用户问题。

如果资料里没有答案，请回答：我在已上传文档里没有找到足够信息。

资料：
{context}

用户问题：
{request.message}
"""

        for part in service.llm.stream_chat(prompt):
            answer_parts.append(part)
            yield part

        full_answer = "".join(answer_parts)
        service.add_message(chat_session_id, "assistant", full_answer)

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/chat/sessions", response_model=list[ChatSessionResponse])
def list_chat_sessions(db: Session = Depends(get_db)) -> list:
    """返回所有聊天会话，按最新创建的会话排在前面。"""
    service = ChatService(db)
    return service.list_sessions()

@router.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
def list_chat_messages(session_id: int, db: Session = Depends(get_db)) -> list:
    """返回指定会话下的用户消息和助手消息。"""
    service = ChatService(db)
    chat_session = service.get_session(session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="聊天会话不存在")

    return service.list_messages(session_id)

@router.get("/chat/sessions/{session_id}/rag-logs", response_model=list[RagCallLogResponse])
def list_rag_logs(session_id: int, db: Session = Depends(get_db)) -> list:
    """返回指定会话下每次 RAG 调用的检索资料、回答和耗时。"""
    service = ChatService(db)
    chat_session = service.get_session(session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="聊天会话不存在")

    return service.list_rag_logs(session_id)

@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: int, db: Session = Depends(get_db)) -> dict[str, int | str]:
    """删除指定聊天会话及其下的聊天消息。"""
    service = ChatService(db)
    deleted = service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="聊天会话不存在")

    return {
        "session_id": session_id,
        "message": "聊天会话已删除",
    }
