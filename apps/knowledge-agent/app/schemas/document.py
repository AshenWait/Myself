from datetime import datetime

from pydantic import BaseModel


#定义了接口返回的数据格式
class DocumentResponse(BaseModel):
    """文档接口响应体，返回上传文档的元数据。"""

    id: int
    filename: str
    file_path: str
    content_type: str
    page_count: int
    created_at: datetime


class ChunkResponse(BaseModel):
    """文档 chunk 响应体，返回切片内容和位置信息。"""

    id: int
    document_id: int
    content: str
    page_number: int
    chunk_index: int
    created_at: datetime
