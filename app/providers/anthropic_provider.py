"""
app/providers/anthropic_provider.py — Anthropic Claude 供應商
注意：Anthropic 無官方 Embedding API
      Embedding 部分 fallback 到 Ollama nomic-embed-text
"""
import anthropic
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.providers.base import BaseAIProvider, LLMResponse
from app.config import get_settings

settings = get_settings()


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude 供應商（LLM 生成 + Ollama Embedding）"""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("❌ ANTHROPIC_API_KEY 未設定，請在 .env 填入")
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._llm_model = settings.anthropic_llm_model
        # Anthropic 無 Embedding API，fallback 到 Ollama
        self._embed_client = None
        self._init_embed_fallback()
        logger.info(f"🎭 Anthropic 供應商初始化: LLM={self._llm_model}, Embed=Ollama(fallback)")

    def _init_embed_fallback(self):
        """初始化 Ollama 作為 Embedding fallback"""
        try:
            import ollama
            self._embed_client = ollama.Client(host=settings.ollama_base_url)
            logger.info("✅ Anthropic Embedding fallback: Ollama 已連接")
        except Exception as e:
            logger.warning(f"⚠️ Ollama Embedding fallback 初始化失敗: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """調用 Anthropic Claude 生成回應"""
        try:
            message = self._client.messages.create(
                model=self._llm_model,
                max_tokens=2048,
                system=system_prompt or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = message.content[0].text
            return LLMResponse(
                content=content,
                model=self._llm_model,
                provider=self.provider_name,
                tokens_used=message.usage.input_tokens + message.usage.output_tokens,
            )
        except Exception as e:
            logger.error(f"❌ Anthropic generate 失敗: {e}")
            raise

    def embed(self, text: str) -> list[float]:
        """Embedding fallback 到 Ollama"""
        if not self._embed_client:
            raise RuntimeError("❌ Embedding fallback (Ollama) 不可用，請確認 Ollama 已啟動")
        try:
            response = self._embed_client.embeddings(
                model=settings.ollama_embed_model, prompt=text
            )
            return response["embedding"]
        except Exception as e:
            logger.error(f"❌ Anthropic/Ollama embed 失敗: {e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def health_check(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception as e:
            logger.warning(f"⚠️ Anthropic 健康檢查失敗: {e}")
            return False

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def embed_dimensions(self) -> int:
        return 768  # Ollama nomic-embed-text
