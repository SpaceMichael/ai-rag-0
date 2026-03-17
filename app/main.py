"""
app/main.py — FastAPI 應用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from app.config import get_settings
from app.database import init_db

settings = get_settings()

# 設定日誌格式
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | {message}",
    colorize=True,
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用啟動和關閉生命週期"""
    logger.info("🚀 ai-rag-0 啟動中...")
    logger.info(f"🔌 AI 供應商: {settings.ai_provider.value}")
    logger.info(f"🗄️ 數據庫: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")

    # 初始化數據庫
    init_db()

    # 預初始化 AI 供應商（啟動時進行健康檢查）
    try:
        from app.providers.factory import get_ai_provider
        get_ai_provider()
        logger.info("✅ AI 供應商初始化成功")
    except Exception as e:
        logger.error(f"❌ AI 供應商初始化失敗: {e}")
        raise

    logger.info("✅ ai-rag-0 已就緒！")
    yield
    logger.info("👋 ai-rag-0 關閉中...")


app = FastAPI(
    title="ai-rag-0 知識庫 API",
    description="RAG（檢索增強生成）內部知識庫搜尋系統，支援多AI供應商，內建防幻覺機制",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注冊路由
from app.api import upload, query, health
app.include_router(health.router, prefix="/api/v1", tags=["健康檢查"])
app.include_router(upload.router, prefix="/api/v1", tags=["文件上傳"])
app.include_router(query.router, prefix="/api/v1", tags=["問答查詢"])


@app.get("/")
def root():
    return {
        "service": "ai-rag-0",
        "version": "1.0.0",
        "provider": settings.ai_provider.value,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
