from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.document import ChunkResponse, DocumentResponse
from app.services.document import DocumentService
from app.services.document_parser import parse_document
from app.services.text_splitter import split_pages
from app.services.embedding import EmbeddingService

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = Path("storage/uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown"}


@router.post("/upload")
def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),  # 每次处理上传请求时，自动帮我们创建一个数据库 Session，传给 db
) -> dict[str, str | int | None]:
    """上传文档，完成文件校验、解析、切分、生成向量，并保存文档与 chunk。"""
    # 类型检验/限制大小
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="只支持上传 PDF、txt、markdown 文件")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)  # 表示目录不存在就创建，存在也不报错
    content = file.file.read()  # 读取上传文件内容

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件不能为空")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件不能超过 10MB")

    file_path = UPLOAD_DIR / filename  # 拼接路径
    if file_path.exists():
        file_path = UPLOAD_DIR / f"{file_path.stem}-{uuid4().hex[:8]}{file_path.suffix}"
    file_path.write_bytes(content)  # 保存上传文件

    #解析文件拿到列表数据[{页码：文本}]
    try:
        pages = parse_document(str(file_path), filename)  # 解析文档，返回统一列表list[dict[str, int | str]]
    except Exception as exc:
        raise HTTPException(status_code=400, detail="文档解析失败，请检查文件是否损坏") from exc

    has_text = any(str(page["text"]).strip() for page in pages)
    if not has_text:
        raise HTTPException(status_code=400, detail="文档没有可解析文本，请检查文件内容")

    service = DocumentService(db)#用来操作数据库

    # 保存文档元数据到数据库
    document = service.create_document(
        filename=filename,
        file_path=str(file_path),
        content_type=file.content_type or "",
        page_count=len(pages),
    )
    chunks = split_pages(
        pages,
        chunk_size=settings.rag_chunk_size,
        overlap=settings.rag_chunk_overlap,
    ) #[{页码，切片码，文本}]

    embedding_service = EmbeddingService()  #初始化向量服务器
    for chunk in chunks:
        chunk["embedding"] = embedding_service.embed_text(str(chunk["content"])) #将文本转为向量赋值给embedding字段
        chunk["embedding_model"] = embedding_service.model  #向量模型

    saved_chunks = service.create_chunks(document.id, chunks)
    return {
        "document_id": document.id,
        "filename": filename,
        "content_type": file.content_type,
        "file_path": str(file_path),
        "page_count": len(pages),
        "chunk_count": len(saved_chunks),
    }


@router.get("", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)) -> list[dict]:
    """返回所有已上传文档的元数据列表。"""
    service = DocumentService(db)
    documents = service.list_documents()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "content_type": doc.content_type,
            "page_count": doc.page_count,
            "created_at": doc.created_at,
        }
        for doc in documents
    ]

@router.get("/search")
def search_documents(
    query: str,
    limit: int = 3,
    document_id: int | None = None,
    db: Session = Depends(get_db),
):
    """接收搜索文本，生成查询向量，并返回最相似的文档 chunk。"""
    if not query.strip():
        raise HTTPException(status_code=400, detail="搜索内容不能为空")
    if limit < 1 or limit > 10:
        raise HTTPException(status_code=400, detail="limit 必须在 1 到 10 之间")
    embedding_service = EmbeddingService()
    query_embedding = embedding_service.embed_text(query)
    service = DocumentService(db)

    chunk_results = service.search_similar_chunks(
        query_embedding,
        limit,
        document_id=document_id,
    )

    return [
        {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "distance": distance,
        }
        for chunk, distance in chunk_results
    ]

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)) -> dict:
    """根据文档 id 返回单个文档的元数据。"""
    service = DocumentService(db)
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    return {
        "id": document.id,
        "filename": document.filename,
        "file_path": document.file_path,
        "content_type": document.content_type,
        "page_count": document.page_count,
        "created_at": document.created_at,
    }


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
def list_document_chunks(document_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """返回指定文档下的所有 chunk。"""
    service = DocumentService(db)
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    chunks = service.list_chunks(document_id)
    return [
        {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "created_at": chunk.created_at,
        }
        for chunk in chunks
    ]


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    """根据文档 id 删除文档记录以及它关联的 chunks。"""
    service = DocumentService(db)
    document = service.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = Path(document.file_path)
    deleted = service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    if file_path.exists() and file_path.is_file():
        file_path.unlink()
    return {
        "document_id": document_id,
        "message": "文档已删除",
    }
