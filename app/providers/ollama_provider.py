"""
app/providers/ollama_provider.py — Ollama 本地 AI 供應商
完全本地運行，數據不外洩，適合私隱敏感環境
"""
import ollama
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.providers.base import BaseAIProvider, LLMResponse
from app.config import get_settings

settings = get_settings()


class OllamaProvider(BaseAIProvider):
    """Ollama 本地 AI 供應商"""

    def __init__(self):
        self._client = ollama.Client(host=settings.ollama_base_url)
        self._llm_model = settings.ollama_llm_model
        self._embed_model = settings.ollama_embed_model
        logger.info(f"🦙 Ollama 供應商初始化: LLM={self._llm_model}, Embed={self._embed_model}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """調用 Ollama LLM 生成回應"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat(
                model=self._llm_model,
                messages=messages,
                options={"temperature": 0.1},  # 低 temperature = 更確定性，減少幻覺
            )
            content = response["message"]["content"]
            return LLMResponse(
                content=content,
                model=self._llm_model,
                provider=self.provider_name,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"❌ Ollama generate 失敗: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def embed(self, text: str) -> list[float]:
        """將文字向量化"""
        try:
            response = self._client.embeddings(model=self._embed_model, prompt=text)
            return response["embedding"]
        except Exception as e:
            logger.error(f"❌ Ollama embed 失敗: {e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量向量化"""
        return [self.embed(t) for t in texts]

    def health_check(self) -> bool:
        """確認 Ollama 服務正常"""
        try:
            self._client.list()
            return True
        except Exception as e:
            logger.warning(f"⚠️ Ollama 健康檢查失敗: {e}")
            return False

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def embed_dimensions(self) -> int:
        # nomic-embed-text = 768, mxbai-embed-large = 1024
        dim_map = {"nomic-embed-text": 768, "mxbai-embed-large": 1024}
        return dim_map.get(self._embed_model, 768)
