from sqlalchemy.orm import Session

from app.models.document import Chunk
from app.models.note import Note
from app.services.document import DocumentService
from app.services.embedding import EmbeddingService
from app.services.llm import LLMService


def retrieve_documents(db: Session, query: str, limit: int = 3) -> list[dict]:
    """根据用户问题检索相关文档片段，作为 Agent 的只读工具。"""
    embedding_service = EmbeddingService()
    query_embedding = embedding_service.embed_text(query)

    document_service = DocumentService(db)
    results = document_service.search_similar_chunks(
        query_embedding,
        limit=limit,
    )

    return [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "distance": distance,
        }
        for chunk, distance in results
    ]


def summarize_document(
    db: Session,
    document_id: int,
    max_chunks: int = 8,
) -> dict:
    """总结指定文档，并返回用于生成总结的引用来源。"""
    document_service = DocumentService(db)
    document = document_service.get_document(document_id)

    if document is None:
        raise ValueError("文档不存在")

    chunks = document_service.list_chunks(document_id)
    selected_chunks = chunks[:max_chunks]

    if not selected_chunks:
        raise ValueError("文档没有可总结的内容")

    context = "\n\n".join(
        f"引用 {index + 1}，第 {chunk.page_number} 页：\n{chunk.content}"
        for index, chunk in enumerate(selected_chunks)
    )

    prompt = f"""
你是 Knowledge Agent，请根据下面的文档内容生成总结。

要求：
1. 用中文总结。
2. 先给出 3-5 条要点。
3. 最后给一句整体概括。
4. 不要编造文档里没有的信息。
5. 如果引用具体信息，请使用“引用 1”“引用 2”这样的编号。

文档名：
{document.filename}

文档内容：
{context}
"""

    llm = LLMService()
    summary, latency = llm.chat(prompt)

    sources = [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_filename": document.filename,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
        }
        for chunk in selected_chunks
    ]

    return {
        "document_id": document.id,
        "document_filename": document.filename,
        "summary": summary,
        "latency_ms": int(latency * 1000),
        "sources": sources,
    }

def list_documents(db: Session) -> list[dict]:
    """列出已上传文档，作为 Agent 的只读工具。"""
    document_service = DocumentService(db)
    documents = document_service.list_documents()

    return [
        {
            "document_id": document.id,
            "filename": document.filename,
            "content_type": document.content_type,
            "page_count": document.page_count,
            "created_at": document.created_at.isoformat()
            if document.created_at
            else None,
        }
        for document in documents
    ]


def create_note(
    db: Session,
    title: str,
    content: str,
    source_ids: list[int],
) -> dict:
    """创建笔记，并保留来源 chunk id。"""
    clean_title = title.strip()
    clean_content = content.strip()

    if not clean_title:
        raise ValueError("笔记标题不能为空")
    if not clean_content:
        raise ValueError("笔记内容不能为空")
    if not source_ids:
        raise ValueError("笔记必须保留至少一个来源 chunk")

    chunks = db.query(Chunk).filter(Chunk.id.in_(source_ids)).all()
    found_chunk_ids = {chunk.id for chunk in chunks}
    missing_ids = [chunk_id for chunk_id in source_ids if chunk_id not in found_chunk_ids]

    if missing_ids:
        raise ValueError(f"来源 chunk 不存在：{missing_ids}")

    note = Note(
        title=clean_title,
        content=clean_content,
        source_chunk_ids=source_ids,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return {
        "note_id": note.id,
        "title": note.title,
        "content": note.content,
        "source_chunk_ids": note.source_chunk_ids,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }
