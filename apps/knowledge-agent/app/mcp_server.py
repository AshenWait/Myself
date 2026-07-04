from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.document import Chunk, Document
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("Knowledge Agent MCP")


def _preview_text(text: str, max_length: int = 500) -> str:
    """把过长 chunk 截短，避免 MCP 返回太大。"""
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


@mcp.tool()
def list_documents(limit: int = 20) -> dict:
    """List uploaded documents. Read-only."""
    safe_limit = min(max(limit, 1), 100)

    db = SessionLocal()
    try:
        documents = (
            db.query(Document)
            .order_by(Document.created_at.desc())
            .limit(safe_limit)
            .all()
        )

        return {
            "documents": [
                {
                    "document_id": document.id,
                    "filename": document.filename,
                    "content_type": document.content_type,
                    "page_count": document.page_count,
                    "created_at": (
                        document.created_at.isoformat()
                        if document.created_at is not None
                        else None
                    ),
                }
                for document in documents
            ]
        }
    finally:
        db.close()


@mcp.tool()
def search_documents(query: str, limit: int = 3) -> dict:
    """Search document chunks by keyword. Read-only."""
    clean_query = query.strip()
    if not clean_query:
        return {"query": query, "results": []}

    safe_limit = min(max(limit, 1), 10)
    pattern = f"%{clean_query}%"

    db = SessionLocal()
    try:
        statement = (
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.content.ilike(pattern))
            .order_by(Document.created_at.desc(), Chunk.chunk_index.asc())
            .limit(safe_limit)
        )

        rows = db.execute(statement).all()

        return {
            "query": clean_query,
            "results": [
                {
                    "document_id": document.id,
                    "filename": document.filename,
                    "chunk_id": chunk.id,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "content": _preview_text(chunk.content),
                }
                for chunk, document in rows
            ],
        }
    finally:
        db.close()


if __name__ == "__main__":
    try:
        mcp.run()
    except KeyboardInterrupt:
        pass
