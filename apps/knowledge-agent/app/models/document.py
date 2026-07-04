from datetime import datetime
from pgvector.sqlalchemy import Vector

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column#mapped_column(...) 表示这个字段在数据库里怎么定义

#Base 是所有 ORM 模型的基类。
#你的 Document(Base)、Chunk(Base) 继承它之后，SQLAlchemy 才知道：这两个类要变成数据库表。
from app.models.base import Base

#表模板
class Document(Base):
    """文档表，保存上传文件的元数据。"""

    __tablename__ = "documents"#Document 这个 Python 类对应数据库里的 documents 表
    id: Mapped[int] = mapped_column(primary_key=True, index=True)#primary_key=True这是主键/index=True给这个字段建索引，查询更快
    filename: Mapped[str] = mapped_column(String(255), nullable=False)#nullable=False   不能为空
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)#保存路径
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)#文件类型
    page_count: Mapped[int] = mapped_column(Integer, default=0)#页数
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())#创建时间，由数据库服务器自动填当前时间，而不是 Python 手动填


class Chunk(Base):
    """文档切片表，保存 chunk 原文、页码、向量和向量模型。"""

    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)#这是外键，表示这个 chunk 属于哪篇文档
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=0)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

