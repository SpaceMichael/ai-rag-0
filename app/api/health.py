"""
app/api/health.py — 健康檢查 API
"""
from fastapi import APIRouter
from loguru import logger
from app.config import get_settings
from app.providers.factory import get_ai_provider

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health_check():
    """系統健康檢查"""
    provider = None
    ai_status = "unknown"

    try:
        provider = get_ai_provider()
        ai_status = "ok" if provider.health_check() else "degraded"
    except Exception as e:
        ai_status = f"error: {str(e)[:100]}"

    return {
        "status": "ok" if ai_status == "ok" else "degraded",
        "service": "ai-rag-0",
        "ai_provider": settings.ai_provider.value,
        "ai_provider_status": ai_status,
        "model": settings.active_llm_model,
        "embed_model": settings.active_embed_model,
    }
