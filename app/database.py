"""
app/database.py — PostgreSQL + pgvector 數據庫連接
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from loguru import logger
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # 自動偵測斷線並重連
    pool_size=5,
    max_overflow=10,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Document(Base):
    """向量文件表"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(500), nullable=False, comment="來源文件名/URL")
    chunk_index = Column(Integer, nullable=False, comment="分塊索引")
    content = Column(Text, nullable=False, comment="原始文字內容")
    embedding = Column(Vector(settings.embed_dimensions), comment="向量")
    doc_metadata = Column(JSON, default={}, comment="額外資訊")
    provider = Column(String(50), comment="生成此向量的AI供應商")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def get_db():
    """FastAPI 依賴注入：取得 DB Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化數據庫：建立表和索引"""
    try:
        with engine.connect() as conn:
            # 啟用 pgvector 擴充
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("✅ pgvector 擴充已啟用")

        # 建立所有表
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 數據庫表建立完成")

        # 建立向量索引（提升搜尋效能）
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS documents_embedding_idx
                ON documents USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            conn.commit()
            logger.info("✅ 向量索引建立完成")

    except Exception as e:
        logger.error(f"❌ 數據庫初始化失敗: {e}")
        raise
