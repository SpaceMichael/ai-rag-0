"""
app/retrieval/vector_store.py — PostgreSQL + pgvector 向量存儲操作
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger
from app.database import Document
from app.providers.base import BaseAIProvider
from app.ingestion.chunker import TextChunk
from app.config import get_settings

settings = get_settings()


class VectorStore:
    """向量數據庫操作封裝"""

    def __init__(self, db: Session, provider: BaseAIProvider):
        self.db = db
        self.provider = provider

    def add_chunks(self, chunks: list[TextChunk]) -> int:
        """批量寫入 Chunk 及其向量到 PostgreSQL"""
        texts = [c.content for c in chunks]
        logger.info(f"⚡ 向量化 {len(texts)} 個 Chunk...")
        embeddings = self.provider.embed_batch(texts)

        records = []
        for chunk, embedding in zip(chunks, embeddings):
            records.append(Document(
                source=chunk.source,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=embedding,
                doc_metadata=chunk.metadata,
                provider=self.provider.provider_name,
            ))

        self.db.bulk_save_objects(records)
        self.db.commit()
        logger.info(f"✅ 成功寫入 {len(records)} 個向量記錄")
        return len(records)

    def similarity_search(self, query: str, top_k: int = None) -> list[dict]:
        """
        余弦相似度搜尋：找最相關的 Top-K 文件塊
        返回包含 content + score + source 的字典列表
        """
        top_k = top_k or settings.top_k_results
        query_embedding = self.provider.embed(query)

        results = self.db.execute(
            text("""
                SELECT
                    id,
                    source,
                    chunk_index,
                    content,
                    doc_metadata,
                    1 - (embedding <=> CAST(:embedding AS vector)) AS similarity_score
                FROM documents
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            {"embedding": str(query_embedding), "top_k": top_k},
        ).fetchall()

        docs = []
        for row in results:
            docs.append({
                "id": row.id,
                "source": row.source,
                "chunk_index": row.chunk_index,
                "content": row.content,
                "metadata": row.doc_metadata,
                "similarity_score": float(row.similarity_score),
            })

        logger.debug(f"🔍 搜尋完成，找到 {len(docs)} 個相關文件 (top {top_k})")
        return docs

    def delete_by_source(self, source: str) -> int:
        """刪除指定來源的所有文件塊"""
        count = self.db.query(Document).filter(Document.source == source).count()
        self.db.query(Document).filter(Document.source == source).delete()
        self.db.commit()
        logger.info(f"🗑️ 已刪除 [{source}] 的 {count} 個記錄")
        return count

    def list_sources(self) -> list[str]:
        """列出所有已上傳的文件來源"""
        results = self.db.execute(
            text("SELECT DISTINCT source FROM documents ORDER BY source")
        ).fetchall()
        return [r.source for r in results]

    def get_stats(self) -> dict:
        """取得知識庫統計資訊"""
        total = self.db.query(Document).count()
        sources = len(self.list_sources())
        return {"total_chunks": total, "total_sources": sources}
