from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatSession, ChatMessage
from app.models.rag import RagCallLog
from app.services.document import DocumentService
from app.services.embedding import EmbeddingService
from app.services.llm import LLMService
from app.services.output_guardrails import (
    build_output_refusal,
    check_answer_output,
    log_output_check,
)
from app.services.trace import TraceRecorder, elapsed_ms, now_ms




class ChatService:
    """聊天业务服务，负责会话、消息、RAG 问答和 RAG 调用日志。"""

    def __init__(self, db:Session):
        """初始化聊天服务，并创建 LLM、Embedding 和文档服务实例。"""
        self.db = db
        self.trace_recorder = TraceRecorder(db)
        self.llm = LLMService(trace_recorder=self.trace_recorder)
        self.embedding = EmbeddingService()
        self.document_service = DocumentService(db)
    
    def build_session_title(self, message: str, max_length: int = 30) -> str:
        """根据用户第一句话生成会话标题，过长时自动截断。"""
        title = message.strip().replace("\n", " ")
        if not title:
            return "New Chat"
        if len(title) > max_length:
            return title[:max_length] + "..."
        return title

    def create_session(self, title:str) -> ChatSession:
        """创建新的聊天会话，并返回数据库生成后的会话对象。"""
        session = ChatSession(title=title)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def add_message(self, session_id: int, role: str, content: str) -> ChatMessage:
        """往指定会话里保存一条用户或助手消息。"""
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def add_rag_log(
            self,
            session_id: int,
            question: str,
            answer: str,
            latency_ms: int,
            retrieved_chunks: list[dict]
    ) -> RagCallLog:
        """保存一次 RAG 调用日志，包括问题、回答、耗时和检索资料。"""
        log = RagCallLog(
            session_id=session_id,
            question=question,
            answer=answer,
            latency_ms=latency_ms,
            retrieved_chunks=retrieved_chunks,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_session(self, session_id: int) -> ChatSession | None:
        """根据会话 id 获取聊天会话，不存在时返回 None。"""
        #从数据库中查询 ChatSession表，找到 id = session_id的那一条记录，并返回它（如果没有则返回 None）
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    def list_sessions(self) -> list[ChatSession]:
        """获取所有聊天会话，按 id 倒序排列。"""
        return self.db.query(ChatSession).order_by(ChatSession.id.desc()).all()

    def list_messages(self, session_id: int) -> list[ChatMessage]:
        """获取某个聊天会话下的所有消息，按发送顺序排列。"""
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
            .all()
        )

    def list_rag_logs(self, session_id: int) -> list[RagCallLog]:
        """获取某个会话下的 RAG 调用日志，按调用顺序排列。"""
        return (
            self.db.query(RagCallLog)
            .filter(RagCallLog.session_id == session_id)
            .order_by(RagCallLog.id)
            .all()
        )

    def delete_session(self, session_id: int) -> bool:
        """删除聊天会话和它下面的所有消息；不存在时返回 False。"""
        chat_session = self.get_session(session_id)
        if chat_session is None:
            return False

        self.db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
        self.db.delete(chat_session)
        self.db.commit()
        return True

    def list_recent_messages(self, session_id: int, limit: int = 6) -> list[ChatMessage]:
        """获取某个会话最近几条消息，用于拼接聊天历史上下文。"""
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(messages))

    def chat(
        self,
        user_message: str,
        document_id: int | None = None,
        session_id: int | None = None,
    ) -> tuple[str, float, list[dict[str, int | str | float]], str]:
        """执行一次 RAG 问答，返回模型回答、耗时和引用来源。"""
        retrieval_start_ms = now_ms()
        query_embedding = self.embedding.embed_text(user_message)   #问题转向量
        # 相似度搜索返回 [(chunk1, 0.12), (chunk2, 0.35)]，distance 越小越相关
        chunk_results = self.document_service.search_similar_chunks(
            query_embedding,
            limit=settings.rag_top_k,
            document_id=document_id,
        )
        #排除阈值外的
        relevant_results = [
            (chunk, distance)
            for chunk, distance in chunk_results
            if distance <= settings.max_rag_distance
        ]
        self.trace_recorder.record(
            tool_name="retrieve_documents",
            input_data={
                "type": "rag_retrieval",
                "query": user_message,
                "document_id": document_id,
                "limit": settings.rag_top_k,
            },
            output_data={
                "retrieved_count": len(chunk_results),
                "relevant_count": len(relevant_results),
                "preview": [
                    {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "distance": distance,
                    }
                    for chunk, distance in relevant_results[:3]
                ],
            },
            latency_ms=elapsed_ms(retrieval_start_ms),
            status="success",
        )
        if not relevant_results:
            answer = "我在已上传文档里没有找到足够信息。"
            output_result = check_answer_output(answer, [])
            log_output_check(self.db, user_message, answer, output_result)
            return answer, 0.0, [], self.trace_recorder.run_id

        #大模型只认文本，所以要把无关字段剔除
        context = "\n\n".join(
            f"资料{index+1}:\n{chunk.content}"
            for index, (chunk, distance) in enumerate(relevant_results)
        )
        history_text = ""
        if session_id is not None:
            recent_messages = self.list_recent_messages(
                session_id,
                limit=settings.chat_history_limit,
            )
            history_text = "\n".join(
                f"{message.role}: {message.content}"
                for message in recent_messages
            )
        prompt = f"""
你是 Knowledge Agent，请根据下面的资料和聊天历史回答用户问题。

如果资料里没有答案，请回答：我在已上传文档里没有找到足够信息。

聊天历史：
{history_text}

资料：
{context}

用户问题：
{user_message}
"""
        #访问大模型,回答与请求耗时
        answer, latency = self.llm.chat(prompt)
        #返回给响应体
        sources = self.build_sources(relevant_results)

        output_result = check_answer_output(answer, sources)
        log_output_check(self.db, user_message, answer, output_result)

        if not output_result.allowed:
            return build_output_refusal(output_result), latency, [], self.trace_recorder.run_id

        return answer, latency, sources, self.trace_recorder.run_id

    def build_sources(self, relevant_results) -> list[dict[str, int | str | float]]:
        """把检索命中的 chunk 转成前端引用来源结构。"""
        sources = []
        for chunk, distance in relevant_results:
            document = self.document_service.get_document(chunk.document_id)
            sources.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_filename": document.filename if document else "",
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "distance": distance,
                }
            )
        return sources

