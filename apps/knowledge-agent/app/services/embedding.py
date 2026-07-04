from openai import OpenAI

from app.core.config import settings


class EmbeddingService:
    """Embedding 服务，负责把文本转换成向量。"""

    def __init__(self) -> None:
        """初始化兼容 OpenAI 协议的百炼 embedding 客户端。"""
        self.client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.model = settings.embedding_model

    def embed_text(self, text: str) -> list[float]:
        """调用 embedding API，把一段文本转换成向量列表。"""
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding
