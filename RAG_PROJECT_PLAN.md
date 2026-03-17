# 🤖 ai-rag-0 — RAG 內部知識庫系統 實施計劃書

> 作者：Sally（超級軟件工程師）  
> 日期：2026-03-17  
> 版本：v1.0

---

## 📌 項目概覽

| 項目 | 詳情 |
|------|------|
| **項目名稱** | ai-rag-0 |
| **核心功能** | RAG（檢索增強生成）內部知識庫搜尋系統 |
| **AI 引擎** | Ollama（本地 AI，完全私隱） |
| **文件類型** | 混合（PDF、Word、CSV、TXT、網頁等） |
| **向量數據庫** | PostgreSQL + pgvector 擴充 |
| **後端** | Python + FastAPI |
| **前端** | Streamlit（簡單 Web UI） |
| **語言** | Python 3.11+ |

---

## 🏗️ 系統架構圖

```
┌─────────────────────────────────────────────────────┐
│                   使用者 (User)                      │
│           (Streamlit Web UI 問問題)                  │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP Request
                      ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI 後端 (RAG Engine)               │
│  ┌─────────────┐    ┌──────────────┐                │
│  │ Query 處理  │───▶│ Embedding 化 │                │
│  └─────────────┘    └──────┬───────┘                │
│                            │                         │
│                            ▼                         │
│                  ┌──────────────────┐                │
│                  │ 向量相似度搜尋   │                │
│                  │ (pgvector)       │                │
│                  └──────┬───────────┘                │
│                         │ Top-K 相關文件             │
│                         ▼                            │
│                  ┌──────────────────┐                │
│                  │ Prompt 組裝      │                │
│                  │ (Context + Query)│                │
│                  └──────┬───────────┘                │
│                         │                            │
│                         ▼                            │
│                  ┌──────────────────┐                │
│                  │  Ollama Local AI │                │
│                  │  (LLM 生成答案)  │                │
│                  └──────┬───────────┘                │
│                         │                            │
│                         ▼                            │
│                  ┌──────────────────┐                │
│                  │  自我驗証模組    │                │
│                  │  (Hallucination  │                │
│                  │   Detection)     │                │
│                  └──────┬───────────┘                │
└─────────────────────────┼───────────────────────────┘
                          │ 最終答案 + 來源引用
                          ▼
                    回傳給使用者
```

---

## ✅ 前提條件（Prerequisites）

### 1. 硬件要求

| 項目 | 最低要求 | 建議 |
|------|---------|------|
| RAM | 8GB | 16GB+ |
| GPU | 不需要（CPU mode） | NVIDIA GPU (VRAM 8GB+) |
| 儲存 | 20GB 空閒 | 50GB+ |

### 2. 軟件安裝清單

```bash
# 必裝軟件
✅ Python 3.11+
✅ PostgreSQL 15+（已安裝，見 workspace/postgres）
✅ Ollama（本地 AI 引擎）
✅ Git

# Ollama 安裝（Windows）
# 下載：https://ollama.ai/download

# 下載 Embedding Model（必須）
ollama pull nomic-embed-text    # 輕量 Embedding 模型

# 下載 LLM Model（選擇一個）
ollama pull llama3.2            # 推薦：Llama 3.2 3B（快速）
ollama pull mistral             # 或：Mistral 7B（更準確）
ollama pull phi4                # 或：Phi-4（微軟，中文較好）
```

### 3. PostgreSQL 設定

```sql
-- 啟動 pgvector 擴充
CREATE EXTENSION IF NOT EXISTS vector;

-- 建立知識庫數據庫
CREATE DATABASE ai_rag_db;

-- 建立向量表
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    source TEXT,           -- 文件來源（檔案名/URL）
    chunk_index INT,       -- 分塊索引
    content TEXT,          -- 原始文字內容
    embedding vector(768), -- 向量（nomic-embed-text 係 768 維）
    metadata JSONB,        -- 額外資訊（作者、日期等）
    created_at TIMESTAMP DEFAULT NOW()
);

-- 建立向量索引（加速搜尋）
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

## 📦 Python 套件清單（requirements.txt）

```txt
# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.0
streamlit==1.39.0

# AI / LLM
langchain==0.3.0
langchain-community==0.3.0
langchain-ollama==0.2.0
ollama==0.3.0

# 向量數據庫
pgvector==0.3.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.35

# 文件處理（混合類型）
pypdf2==3.0.1           # PDF
python-docx==1.1.0      # Word
pandas==2.2.0           # CSV/Excel
beautifulsoup4==4.12.3  # HTML/網頁
unstructured==0.15.0    # 萬能文件解析

# Embedding
sentence-transformers==3.0.0

# 驗証 / Debug
ragas==0.1.21           # RAG 評估框架
pytest==8.0.0
python-dotenv==1.0.0
loguru==0.7.2           # 結構化日誌
```

---

## 📁 項目目錄結構

```
ai-rag-0/
├── RAG_PROJECT_PLAN.md     # 本計劃書
├── .env                    # 環境變數（API Keys、DB 連接）
├── .env.example            # 環境變數範例
├── requirements.txt        # Python 套件
├── docker-compose.yml      # Docker（可選）
│
├── app/                    # FastAPI 主應用
│   ├── main.py             # FastAPI 入口
│   ├── config.py           # 設定檔
│   ├── database.py         # PostgreSQL 連接
│   │
│   ├── ingestion/          # 文件攝取模組
│   │   ├── loader.py       # 文件載入（PDF/Word/CSV/HTML）
│   │   ├── chunker.py      # 文字分塊（Chunking）
│   │   └── embedder.py     # 向量化（Embedding）
│   │
│   ├── retrieval/          # 檢索模組
│   │   ├── vector_store.py # pgvector 操作
│   │   └── retriever.py    # 相似度搜尋
│   │
│   ├── generation/         # 生成模組
│   │   ├── llm.py          # Ollama LLM 調用
│   │   ├── prompt.py       # Prompt 模板
│   │   └── chain.py        # RAG Chain 組合
│   │
│   ├── validation/         # 🛡️ 自我驗証模組（防幻覺）
│   │   ├── hallucination_checker.py  # 幻覺檢測
│   │   ├── self_debug.py             # 自我 Debug
│   │   └── confidence_scorer.py      # 信心分數
│   │
│   └── api/                # API 路由
│       ├── upload.py       # 文件上傳 API
│       ├── query.py        # 問答 API
│       └── health.py       # 健康檢查
│
├── ui/                     # Streamlit Web UI
│   └── app.py              # 前端頁面
│
├── tests/                  # 測試
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   ├── test_generation.py
│   └── test_validation.py
│
└── scripts/                # 工具腳本
    ├── init_db.py          # 初始化數據庫
    ├── ingest_docs.py      # 批量攝取文件
    └── evaluate_rag.py     # RAG 評估腳本
```

---

## 🛡️ 防幻覺（Anti-Hallucination）策略

### 核心原則
> **「沒有來源就不回答」**

### 1. Context Grounding（基礎鎖定）

```python
# Prompt 設計：強制 LLM 只用提供的文件回答
SYSTEM_PROMPT = """
你係一個嚴謹的知識庫助手。
規則：
1. 只根據以下提供的文件內容回答
2. 如果文件中找不到答案，直接說「根據現有文件，我找不到相關資訊」
3. 回答時必須引用來源（文件名稱+段落）
4. 絕對不要憑空猜測或編造資訊
5. 如果不確定，說「我不確定，建議人工確認」

文件內容：
{context}
"""
```

### 2. 幻覺檢測（自動驗証）

```python
# validation/hallucination_checker.py
# 策略：用另一個 LLM 驗証答案是否有文件支持

def check_hallucination(answer: str, context: str) -> dict:
    """
    用 Ollama 二次驗証：
    - 答案中每個聲明是否在 context 中找到依據？
    - 返回信心分數（0-1）
    """
    verification_prompt = f"""
    請驗証以下答案是否完全基於提供的文件：
    
    文件：{context}
    答案：{answer}
    
    請逐點檢查，返回 JSON：
    {{"is_grounded": true/false, "confidence": 0.0-1.0, "unsupported_claims": []}}
    """
    # ... 調用 Ollama 驗証
```

### 3. 信心分數系統

| 分數 | 狀態 | 行動 |
|------|------|------|
| 0.9 - 1.0 | ✅ 高信心 | 直接回答 + 來源 |
| 0.7 - 0.9 | ⚠️ 中信心 | 回答 + 警告 + 來源 |
| < 0.7 | ❌ 低信心 | 拒絕回答，建議人工確認 |

### 4. 強制引用來源

每個回答必須包含：
```json
{
  "answer": "根據文件...",
  "sources": [
    {"file": "policy_2024.pdf", "page": 3, "chunk": "...原文..."},
    {"file": "manual.docx", "section": "第2章"}
  ],
  "confidence": 0.92,
  "warning": null
}
```

---

## 🔍 自我驗証 & 自我 Debug 機制

### Self-RAG 流程

```
用戶提問
    │
    ▼
[1] 檢索相關文件（Top-K）
    │
    ▼
[2] 相關性評分：這些文件真的相關嗎？
    │ 不相關？→ 擴大搜尋範圍
    │ 相關？↓
    ▼
[3] LLM 生成答案
    │
    ▼
[4] 幻覺檢測：答案有文件支持嗎？
    │ 有幻覺？→ 重新生成（最多3次）
    │ 無幻覺？↓
    ▼
[5] 格式驗証：答案結構正確嗎？
    │
    ▼
[6] 輸出最終答案 + 信心分數 + 來源
```

### 自動 Debug 日誌

```python
# 使用 loguru 記錄每步過程
logger.info(f"[RETRIEVAL] 找到 {len(docs)} 個相關文件")
logger.info(f"[SCORING] 相關性分數: {scores}")
logger.info(f"[GENERATION] 生成嘗試 #{attempt}")
logger.warning(f"[HALLUCINATION] 檢測到未支持聲明: {claims}")
logger.error(f"[FAILED] 超過最大重試次數，返回安全回應")
```

---

## 🗂️ 開發路線圖（Roadmap）

### Phase 1：基礎設施（1-2天）
- [ ] 安裝 Ollama + 下載模型
- [ ] 設置 PostgreSQL + pgvector
- [ ] 建立 FastAPI 骨架
- [ ] 初始化數據庫表

### Phase 2：文件攝取（2-3天）
- [ ] 實現多類型文件載入器
- [ ] 文字分塊策略（Chunking）
- [ ] Embedding 向量化
- [ ] 批量上傳 API

### Phase 3：RAG 核心（3-4天）
- [ ] 向量相似度搜尋
- [ ] Prompt 模板設計
- [ ] Ollama LLM 調用
- [ ] RAG Chain 組合

### Phase 4：防幻覺模組（2-3天）
- [ ] 幻覺檢測器
- [ ] 信心分數系統
- [ ] 自我驗証循環
- [ ] 來源引用系統

### Phase 5：前端 & 測試（2-3天）
- [ ] Streamlit Web UI
- [ ] RAGAS 評估框架
- [ ] 單元測試
- [ ] 整合測試

---

## ⚙️ 環境變數（.env）

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_rag_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text

# RAG 設定
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
MIN_CONFIDENCE_SCORE=0.7

# 防幻覺設定
MAX_RETRY_ATTEMPTS=3
HALLUCINATION_THRESHOLD=0.8
```

---

## 🧪 RAGAS 評估指標

| 指標 | 說明 | 目標值 |
|------|------|--------|
| **Faithfulness** | 答案是否忠於文件 | > 0.85 |
| **Answer Relevancy** | 答案是否切題 | > 0.80 |
| **Context Precision** | 檢索的文件是否精準 | > 0.75 |
| **Context Recall** | 是否找到所有相關內容 | > 0.70 |

---

## ⚠️ 重要注意事項

1. **私隱保護**：Ollama 完全本地運行，數據不會離開機器
2. **模型選擇**：中文內容建議用 `phi4` 或 `qwen2.5`，英文用 `llama3.2`
3. **Chunking 策略**：Chunk 太大→檢索慢；太小→上下文不足，建議 400-600 tokens
4. **向量維度**：`nomic-embed-text` = 768維，`all-MiniLM` = 384維，必須一致
5. **pgvector 索引**：超過 10,000 文件後必須建立 IVFFlat 或 HNSW 索引

---

*由 Sally（超級軟件工程師）制定 | ai-rag-0 項目*
