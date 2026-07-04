from pydantic import BaseModel, Field


class RetrieveDocumentsInput(BaseModel):
    """retrieve_documents 工具参数。"""

    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=3, ge=1, le=10)


class SummarizeDocumentInput(BaseModel):
    """summarize_document 工具参数。"""

    document_id: int = Field(ge=1)


class ListDocumentsInput(BaseModel):
    """list_documents 工具参数。"""

    pass


class CreateNoteInput(BaseModel):
    """create_note 工具参数。"""

    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_ids: list[int] = Field(min_length=1)
