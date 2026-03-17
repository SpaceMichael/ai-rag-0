"""
app/providers/factory.py — AI 供應商工廠
一個地方管理所有供應商切換邏輯
"""
from functools import lru_cache
from loguru import logger
from app.providers.base import BaseAIProvider
from app.config import get_settings, AIProvider

settings = get_settings()


@lru_cache(maxsize=1)
def get_ai_provider() -> BaseAIProvider:
    """
    工廠函數：根據環境變數 AI_PROVIDER 返回對應供應商
    使用 lru_cache 確保全局單例，避免重複初始化
    """
    provider_type = settings.ai_provider
    logger.info(f"🔌 初始化 AI 供應商: {provider_type.value}")

    if provider_type == AIProvider.OLLAMA:
        from app.providers.ollama_provider import OllamaProvider
        provider = OllamaProvider()

    elif provider_type == AIProvider.GEMINI:
        from app.providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()

    elif provider_type == AIProvider.OPENAI:
        from app.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider()

    elif provider_type == AIProvider.ANTHROPIC:
        from app.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()

    else:
        raise ValueError(f"❌ 不支援的 AI 供應商: {provider_type}")

    # 啟動健康檢查
    if not provider.health_check():
        logger.error(f"❌ {provider_type.value} 供應商健康檢查失敗！")
        raise RuntimeError(f"AI 供應商 {provider_type.value} 不可用，請確認設定")

    logger.info(f"✅ AI 供應商 [{provider_type.value}] 就緒")
    return provider
