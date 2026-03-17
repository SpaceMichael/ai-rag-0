"""
app/providers/openai_provider.py — OpenAI 供應商
同時支援 OpenAI 官方 API 及 Azure OpenAI
"""
from openai import OpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.providers.base import BaseAIProvider, LLMResponse
from app.config import get_settings

settings = get_settings()


class OpenAIProvider(BaseAIProvider):
    """OpenAI AI 供應商"""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("❌ OPENAI_API_KEY 未設定，請在 .env 填入")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._llm_model = settings.openai_llm_model
        self._embed_model = settings.openai_embed_model
        logger.info(f"🤖 OpenAI 供應商初始化: LLM={self._llm_model}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """調用 OpenAI ChatCompletion"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat.completions.create(
                model=self._llm_model,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
            )
            content = response.choices[0].message.content
            return LLMResponse(
                content=content,
                model=self._llm_model,
                provider=self.provider_name,
                tokens_used=response.usage.total_tokens,
            )
        except Exception as e:
            logger.error(f"❌ OpenAI generate 失敗: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def embed(self, text: str) -> list[float]:
        """OpenAI Embedding"""
        try:
            response = self._client.embeddings.create(
                model=self._embed_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ OpenAI embed 失敗: {e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量 Embedding（OpenAI 支援一次多個）"""
        try:
            response = self._client.embeddings.create(
                model=self._embed_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(f"⚠️ OpenAI 批量 embed 失敗: {e}")
            return [self.embed(t) for t in texts]

    def health_check(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception as e:
            logger.warning(f"⚠️ OpenAI 健康檢查失敗: {e}")
            return False

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def embed_dimensions(self) -> int:
        # text-embedding-3-small=1536, text-embedding-3-large=3072, ada-002=1536
        dim_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dim_map.get(self._embed_model, 1536)
