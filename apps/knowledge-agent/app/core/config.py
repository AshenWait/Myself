from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    """项目配置对象，从 .env 读取数据库、模型和 RAG 参数。"""

    app_name: str = "Knowledge Agent"
    app_version: str = "0.1.0"
    environment: str = "local"
    database_url:str
    docker_database_url: str | None = None
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "knowledge_agent"
    postgres_host_port: int = 5433
    api_host_port: int = 8000
    api_image_tag: str = "day66"
    deepseek_api_key:str
    dashscope_api_key: str
    embedding_model: str = "text-embedding-v4"
    rag_chunk_size: int = 500      # 文档切分时每个 chunk 的最大字符数
    rag_chunk_overlap: int = 50    # 相邻 chunk 重叠字符数
    rag_top_k: int = 3            # 相关度取前三条
    max_rag_distance: float = 0.8 # RAG 阈值
    chat_history_limit: int = 6   # 最近6条消息
    max_chat_message_length: int = 2000 # 用户消息长度

    #告诉 Pydantic：请从项目根目录的 .env 文件读取配置，编码用 utf-8。
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
