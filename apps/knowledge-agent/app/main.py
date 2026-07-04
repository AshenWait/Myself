from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.documents import router as document_router
from app.api.traces import router as trace_router
from app.api.health import router as health_router
from app.core.config import settings
from app.api.chat import router as chat_router


app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(document_router)
app.include_router(trace_router)

@app.get("/")
def root() -> dict[str, str]:
    """返回 API 首页信息，提示文档地址和健康检查地址。"""
    return {
        "message": "Knowledge Agent API is running.",
        "docs": "/docs",
        "health": "/health",
    }
