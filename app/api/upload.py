"""
app/api/upload.py — 文件上傳 API
"""
import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from loguru import logger
from pathlib import Path

from app.database import get_db
from app.providers.factory import get_ai_provider
from app.ingestion.loader import DocumentLoader
from app.ingestion.chunker import TextChunker
from app.retrieval.vector_store import VectorStore

router = APIRouter()
loader = DocumentLoader()
chunker = TextChunker()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".html", ".pptx"}


class UploadResponse(BaseModel):
    filename: str
    chunks_created: int
    message: str


class StatsResponse(BaseModel):
    total_chunks: int
    total_sources: int
    sources: list[str]


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上傳文件到知識庫（自動解析、分塊、向量化）"""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的文件類型: {ext}。支援: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        logger.info(f"📤 上傳文件: {file.filename}")
        doc = loader.load(tmp_path)
        doc.source = file.filename  # 用原始文件名作為來源標識

        chunks = chunker.chunk_document(doc)
        if not chunks:
            raise HTTPException(status_code=400, detail="文件內容為空或無法解析")

        provider = get_ai_provider()
        vector_store = VectorStore(db=db, provider=provider)
        count = vector_store.add_chunks(chunks)

        return UploadResponse(
            filename=file.filename,
            chunks_created=count,
            message=f"✅ 成功處理 {file.filename}，生成 {count} 個知識塊",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 上傳失敗: {e}")
        raise HTTPException(status_code=500, detail=f"文件處理失敗: {str(e)}")
    finally:
        os.unlink(tmp_path)


@router.get("/sources", response_model=StatsResponse)
def get_knowledge_base_stats(db: Session = Depends(get_db)):
    """查看知識庫統計資訊"""
    provider = get_ai_provider()
    vector_store = VectorStore(db=db, provider=provider)
    stats = vector_store.get_stats()
    sources = vector_store.list_sources()
    return StatsResponse(
        total_chunks=stats["total_chunks"],
        total_sources=stats["total_sources"],
        sources=sources,
    )


@router.delete("/sources/{source_name}")
def delete_source(source_name: str, db: Session = Depends(get_db)):
    """從知識庫刪除指定文件"""
    provider = get_ai_provider()
    vector_store = VectorStore(db=db, provider=provider)
    count = vector_store.delete_by_source(source_name)
    return {"message": f"已刪除 {source_name} 的 {count} 個知識塊"}
