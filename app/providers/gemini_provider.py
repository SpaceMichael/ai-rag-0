"""
app/providers/gemini_provider.py — Google Gemini AI 供應商
"""
import google.generativeai as genai
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.providers.base import BaseAIProvider, LLMResponse
from app.config import get_settings

settings = get_settings()


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI 供應商"""

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("❌ GEMINI_API_KEY 未設定，請在 .env 填入")
        genai.configure(api_key=settings.gemini_api_key)
        self._llm_model = settings.gemini_llm_model
        self._embed_model = settings.gemini_embed_model
        self._client = genai.GenerativeModel(
            model_name=self._llm_model,
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # 低 temperature 減少幻覺
                max_output_tokens=2048,
            ),
        )
        logger.info(f"💎 Gemini 供應商初始化: LLM={self._llm_model}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """調用 Gemini 生成回應"""
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = self._client.generate_content(full_prompt)
            content = response.text
            return LLMResponse(
                content=content,
                model=self._llm_model,
                provider=self.provider_name,
                tokens_used=response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0,
            )
        except Exception as e:
            logger.error(f"❌ Gemini generate 失敗: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def embed(self, text: str) -> list[float]:
        """Gemini Embedding"""
        try:
            result = genai.embed_content(
                model=self._embed_model,
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"❌ Gemini embed 失敗: {e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量 Embedding"""
        try:
            result = genai.embed_content(
                model=self._embed_model,
                content=texts,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            logger.warning(f"⚠️ Gemini 批量 embed 失敗，改為逐一處理: {e}")
            return [self.embed(t) for t in texts]

    def health_check(self) -> bool:
        """確認 Gemini API 可用"""
        try:
            self.embed("test")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Gemini 健康檢查失敗: {e}")
            return False

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def embed_dimensions(self) -> int:
        return 768  # Gemini embedding-001 = 768 維
