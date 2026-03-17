"""
app/config.py — 全局設定管理
支援多AI供應商動態切換
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from enum import Enum
from functools import lru_cache


class AIProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    # AI 供應商
    ai_provider: AIProvider = AIProvider.OLLAMA

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    # OpenAI
    openai_api_key: str = ""
    openai_llm_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"

    # Gemini
    gemini_api_key: str = ""
    gemini_llm_model: str = "gemini-1.5-flash"
    gemini_embed_model: str = "models/embedding-001"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_llm_model: str = "claude-3-haiku-20240307"

    # PostgreSQL
    database_url: str = "postgresql://postgres:password@localhost:5432/ai_rag_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_rag_db"
    postgres_user: str = "postgres"
    postgres_password: str = ""

    # RAG 參數
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 5
    embed_dimensions: int = 768

    # 防幻覺
    min_confidence_score: float = 0.70
    hallucination_threshold: float = 0.80
    max_retry_attempts: int = 3

    # 應用
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    @field_validator("ai_provider", mode="before")
    @classmethod
    def validate_provider(cls, v):
        """確保供應商值有效"""
        if isinstance(v, str):
            v = v.lower()
        return v

    @property
    def active_llm_model(self) -> str:
        """根據當前供應商返回對應模型名稱"""
        mapping = {
            AIProvider.OLLAMA: self.ollama_llm_model,
            AIProvider.OPENAI: self.openai_llm_model,
            AIProvider.GEMINI: self.gemini_llm_model,
            AIProvider.ANTHROPIC: self.anthropic_llm_model,
        }
        return mapping[self.ai_provider]

    @property
    def active_embed_model(self) -> str:
        """根據當前供應商返回對應 Embedding 模型"""
        mapping = {
            AIProvider.OLLAMA: self.ollama_embed_model,
            AIProvider.OPENAI: self.openai_embed_model,
            AIProvider.GEMINI: self.gemini_embed_model,
            AIProvider.ANTHROPIC: self.ollama_embed_model,  # Anthropic 無 Embedding，用 Ollama
        }
        return mapping[self.ai_provider]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """單例模式：全局只建立一個 Settings 實例"""
    return Settings()
