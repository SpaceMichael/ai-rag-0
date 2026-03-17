"""
scripts/init_db.py — 數據庫初始化腳本
首次部署時執行一次
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from app.database import init_db, engine
from sqlalchemy import text


def main():
    logger.info("🗄️ 開始初始化 ai-rag-0 數據庫...")

    # 建立表和索引
    init_db()

    # 驗証
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM documents")).fetchone()
        logger.info(f"✅ documents 表已建立，目前記錄數: {result[0]}")

        ext = conn.execute(text(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        )).fetchone()
        if ext:
            logger.info("✅ pgvector 擴充已啟用")
        else:
            logger.error("❌ pgvector 未安裝！請執行: CREATE EXTENSION vector;")
            sys.exit(1)

    logger.info("🎉 數據庫初始化完成！")


if __name__ == "__main__":
    main()
