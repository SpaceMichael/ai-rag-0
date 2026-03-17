"""
app/generation/chain.py — RAG 主鏈路
整合：檢索 → 生成 → 驗証 → 自我 Debug 循環
"""
import time
from dataclasses import dataclass, field
from loguru import logger
from app.providers.base import BaseAIProvider
from app.retrieval.vector_store import VectorStore
from app.generation.prompt import RAG_SYSTEM_PROMPT, build_rag_prompt
from app.validation.hallucination_checker import HallucinationChecker, ValidationResult
from app.config import get_settings

settings = get_settings()


@dataclass
class RAGResponse:
    """RAG 最終回應（完整結構）"""
    answer: str
    sources: list[dict]
    confidence_score: float
    verdict: str                    # PASS / FAIL / UNCERTAIN
    warning: str = ""
    attempt_count: int = 1          # 嘗試次數（自我修正用）
    retrieval_count: int = 0        # 找到的文件數
    elapsed_ms: float = 0.0
    provider: str = ""
    debug_log: list[str] = field(default_factory=list)  # 自我 Debug 日誌


class RAGChain:
    """
    RAG 完整鏈路（帶自我驗証 & 自我 Debug）
    流程：
      1. 向量搜尋
      2. 相關性過濾
      3. LLM 生成
      4. 幻覺檢測
      5. 如失敗 → 調整策略重試（最多 max_retry 次）
      6. 最終輸出
    """

    def __init__(self, vector_store: VectorStore, provider: BaseAIProvider):
        self.vector_store = vector_store
        self.provider = provider
        self.checker = HallucinationChecker(provider)
        self.max_retry = settings.max_retry_attempts
        self.min_confidence = settings.min_confidence_score

    def query(self, question: str) -> RAGResponse:
        """執行 RAG 問答（帶自我修正）"""
        start_time = time.time()
        debug_log = []
        top_k = settings.top_k_results

        debug_log.append(f"[START] 問題: {question}")

        for attempt in range(1, self.max_retry + 1):
            debug_log.append(f"[嘗試 #{attempt}] top_k={top_k}")
            logger.info(f"🔄 RAG 嘗試 #{attempt}, top_k={top_k}")

            # 步驟 1：向量搜尋
            docs = self.vector_store.similarity_search(question, top_k=top_k)
            debug_log.append(f"[RETRIEVAL] 找到 {len(docs)} 個文件")

            if not docs:
                logger.warning("⚠️ 向量庫中找不到相關文件")
                debug_log.append("[RETRIEVAL] 無結果，終止")
                break

            # 步驟 2：相關性過濾（只保留相似度 > 0.3 的）
            relevant_docs = [d for d in docs if d["similarity_score"] > 0.3]
            debug_log.append(f"[FILTER] 過濾後剩 {len(relevant_docs)} 個相關文件")

            if not relevant_docs:
                debug_log.append("[FILTER] 無足夠相關文件，提升 top_k 重試")
                top_k = min(top_k * 2, 20)  # 自動擴大搜尋範圍
                continue

            # 步驟 3：組裝 Prompt 並生成
            prompt = build_rag_prompt(question, relevant_docs)
            llm_response = self.provider.generate(
                prompt=prompt,
                system_prompt=RAG_SYSTEM_PROMPT,
            )
            debug_log.append(f"[GENERATE] 模型: {llm_response.model}, Token: {llm_response.tokens_used}")

            # 步驟 4：幻覺檢測
            validation: ValidationResult = self.checker.check(
                answer=llm_response.content,
                context_docs=relevant_docs,
            )
            debug_log.append(
                f"[VALIDATE] 判決={validation.verdict}, "
                f"信心={validation.confidence_score:.2%}, "
                f"未支持聲明={validation.unsupported_claims}"
            )

            # 步驟 5：判斷是否通過
            if validation.verdict == "PASS":
                logger.info(f"✅ 驗証通過！信心分數: {validation.confidence_score:.2%}")
                return self._build_response(
                    answer=llm_response.content,
                    docs=relevant_docs,
                    validation=validation,
                    attempt=attempt,
                    provider=llm_response.provider,
                    start_time=start_time,
                    debug_log=debug_log,
                )

            # 失敗：記錄並調整策略
            logger.warning(
                f"⚠️ 嘗試 #{attempt} 驗証失敗 "
                f"(信心={validation.confidence_score:.2%}, 判決={validation.verdict})"
            )
            debug_log.append(f"[RETRY] 驗証失敗，擴大搜尋重試")
            top_k = min(top_k + 3, 20)

        # 超過最大重試次數，返回安全的失敗回應
        logger.error(f"❌ 超過最大重試次數 ({self.max_retry})，返回安全回應")
        debug_log.append("[FAILED] 超過最大重試，返回降級回應")

        return RAGResponse(
            answer="根據現有知識庫文件，未能找到可靠的答案。建議查閱其他來源或諮詢相關人員。",
            sources=[],
            confidence_score=0.0,
            verdict="FAIL",
            warning="⚠️ 系統無法找到可信的答案，請人工確認。",
            attempt_count=self.max_retry,
            elapsed_ms=(time.time() - start_time) * 1000,
            provider=self.provider.provider_name,
            debug_log=debug_log,
        )

    def _build_response(
        self,
        answer: str,
        docs: list[dict],
        validation: ValidationResult,
        attempt: int,
        provider: str,
        start_time: float,
        debug_log: list[str],
    ) -> RAGResponse:
        """組裝最終回應"""
        sources = [
            {
                "file": d["source"],
                "chunk_index": d["chunk_index"],
                "similarity": round(d["similarity_score"], 4),
                "excerpt": d["content"][:200] + "..." if len(d["content"]) > 200 else d["content"],
            }
            for d in docs
        ]
        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence_score=validation.confidence_score,
            verdict=validation.verdict,
            warning=validation.warning_message,
            attempt_count=attempt,
            retrieval_count=len(docs),
            elapsed_ms=round((time.time() - start_time) * 1000, 2),
            provider=provider,
            debug_log=debug_log,
        )
