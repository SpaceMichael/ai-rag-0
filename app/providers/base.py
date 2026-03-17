"""
app/providers/base.py — AI 供應商抽象基類（Strategy Pattern）
所有供應商必須實現此介面，確保可互換
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """統一的 LLM 回應格式"""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    raw_response: dict = None


class BaseAIProvider(ABC):
    """
    AI 供應商抽象基類
    無論使用 Ollama / Gemini / OpenAI，介面完全一致
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """
        生成文字回應
        :param prompt: 用戶問題 + Context
        :param system_prompt: 系統指令（角色設定）
        :return: LLMResponse
        """
        pass

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        將文字轉為向量
        :param text: 輸入文字
        :return: 浮點數向量列表
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        批量向量化（效率更高）
        :param texts: 文字列表
        :return: 向量列表
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        健康檢查：確認供應商可用
        :return: True=正常, False=不可用
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """供應商名稱"""
        pass

    @property
    @abstractmethod
    def embed_dimensions(self) -> int:
        """Embedding 向量維度"""
        pass
