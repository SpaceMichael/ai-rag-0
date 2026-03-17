"""
app/api/query.py — 問答查詢 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from loguru import logger

from app.database import get_db
from app.providers.factory import get_ai_provider
from app.retrieval.vector_store import VectorStore
from app.generation.chain import RAGChain, RAGResponse

router = APIRouter()


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="問題")
    top_k: int = Field(default=5, ge=1, le=20, description="返回文件數量")
    include_debug: bool = Field(default=False, description="是否包含 Debug 日誌")


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence_score: float
    verdict: str
    warning: str
    attempt_count: int
    elapsed_ms: float
    provider: str
    debug_log: list[str] = []


@router.post("/query", response_model=QueryResponse)
def query_knowledge_base(
    request: QueryRequest,
    db: Session = Depends(get_db),
):
    """
    向知識庫提問
    - 自動檢索相關文件
    - LLM 生成答案
    - 幻覺檢測驗証
    - 返回信心分數和來源
    """
    logger.info(f"📥 收到問題: {request.question[:100]}")

    provider = get_ai_provider()
    vector_store = VectorStore(db=db, provider=provider)
    chain = RAGChain(vector_store=vector_store, provider=provider)

    try:
        result: RAGResponse = chain.query(request.question)
    except Exception as e:
        logger.error(f"❌ 查詢失敗: {e}")
        raise HTTPException(status_code=500, detail=f"查詢處理失敗: {str(e)}")

    return QueryResponse(
        answer=result.answer,
        sources=result.sources,
        confidence_score=result.confidence_score,
        verdict=result.verdict,
        warning=result.warning,
        attempt_count=result.attempt_count,
        elapsed_ms=result.elapsed_ms,
        provider=result.provider,
        debug_log=result.debug_log if request.include_debug else [],
    )
