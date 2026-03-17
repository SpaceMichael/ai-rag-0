# 🤖 ai-rag-0 — RAG 知識庫系統 完整計劃書 V2

> Sally（超級軟件工程師）制定  
> 日期：2026-03-17 | 版本：v2.0（含設計漏洞審查）

---

## 📌 一、項目概覽

| 項目 | 詳情 |
|------|------|
| **項目名稱** | ai-rag-0 |
| **核心功能** | RAG 內部知識庫搜尋，支援多AI供應商動態切換 |
| **AI 引擎** | Ollama（本地）/ Gemini / OpenAI / Anthropic（可切換） |
| **向量數據庫** | PostgreSQL + pgvector |
| **後端** | Python 3.11+ + FastAPI |
| **前端** | Streamlit Web UI |
| **文件支援** | PDF / Word / CSV / Excel / TXT / HTML / PPT |

---

## ✅ 二、前提條件清單（物品清單）

### 🖥️ 硬件要求

| 項目 | 最低 | 建議 |
|------|------|------|
| RAM | 8 GB | 16 GB+ |
| CPU | 4 核 | 8 核+ |
| 儲存 | 20 GB | 50 GB+ |
| GPU | 不需要（CPU 運行） | NVIDIA 8GB+ VRAM（加速） |

### 📦 必裝軟件清單

```
□ Python 3.11 或以上
  下載：https://python.org/downloads

□ PostgreSQL 15 或以上
  下載：https://postgresql.org/download
  安裝後啟用 pgvector 擴充：
    CREATE EXTENSION vector;

□ Ollama（如用本地 AI）
  下載：https://ollama.ai/download
  安裝後下載模型：
    ollama pull nomic-embed-text    # Embedding 模型（必須）
    ollama pull llama3.2            # LLM 模型（推薦入門）
    ollama pull phi4                # 中文較佳選擇

□ Git
  下載：https://git-scm.com

□ pip（Python 套件管理，隨 Python 附帶）
```

### 🔑 API Keys 清單（按需填入 .env）

```
□ AI_PROVIDER 設定（選一個）：
  - Ollama：不需要 API Key（本地）
  - OpenAI：OPENAI_API_KEY=sk-xxxx
  - Gemini：GEMINI_API_KEY=AIzaSyxxxx
  - Anthropic：ANTHROPIC_API_KEY=sk-ant-xxxx

□ PostgreSQL 連接資訊：
  - POSTGRES_HOST（通常 localhost）
  - POSTGRES_PORT（預設 5432）
  - POSTGRES_DB=ai_rag_db
  - POSTGRES_USER
  - POSTGRES_PASSWORD
```

### 🐍 Python 套件

見 `requirements.txt`（執行 `pip install -r requirements.txt` 安裝）

---

## 🏗️ 三、系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web UI                         │
│              （上傳文件 / 提問 / 查看來源）                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI 後端 (RAG Engine)                  │
│                                                             │
│  POST /upload ──→ [Loader] ──→ [Chunker] ──→ [Embedder]   │
│                                                 │           │
│                                           [VectorStore]     │
│                                           (PostgreSQL+      │
│                                            pgvector)        │
│                                                             │
│  POST /query ──→ [向量搜尋] ──→ [Prompt組裝] ──→ [LLM]   │
│                      │                              │        │
│                   Top-K文件                      答案草稿   │
│                                                    │        │
│                                          [幻覺檢測器]       │
│                                          信心分數 < 0.7?    │
│                                          ├─ 是 → 重試       │
│                                          └─ 否 → 輸出       │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌─────────────────┐      ┌──────────────────────┐
   │ PostgreSQL DB   │      │   AI Provider        │
   │ + pgvector      │      │  （可熱切換）        │
   │                 │      │  Ollama / Gemini /   │
   │  documents 表   │      │  OpenAI / Anthropic  │
   └─────────────────┘      └──────────────────────┘
```

---

## 💻 四、使用語言及框架選擇原因

| 技術 | 選擇原因 |
|------|---------|
| **Python 3.11+** | AI/ML 生態最完善，LangChain、pgvector、Ollama 庫首選語言 |
| **FastAPI** | 高性能異步框架，自動生成 OpenAPI 文檔，Pydantic 資料驗証 |
| **Streamlit** | 純 Python 寫前端，無需 HTML/JS，快速原型 |
| **PostgreSQL + pgvector** | 企業級穩定，已有基礎設施，pgvector 原生支援余弦相似度搜尋 |
| **Strategy Pattern（供應商）** | 一個介面，多個實現，無需改業務代碼即可切換 AI |
| **Pydantic** | 強類型驗証，防止垃圾資料進入系統 |
| **Loguru** | 結構化日誌，方便長期維護和問題追蹤 |
| **Tenacity** | 自動重試，應對 AI API 暫時性錯誤 |

---

## 🛡️ 五、防幻覺策略（完整）

### 5.1 Prompt 層面
```
規則一：只根據提供文件回答
規則二：找不到答案 → 明確說找不到（不猜測）
規則三：每個回答必須引用來源
規則四：不確定 → 明確說不確定
Temperature = 0.1（低隨機性 = 更確定性輸出）
```

### 5.2 相似度過濾
- 相似度分數 < 0.3 的文件自動過濾
- 沒有足夠相關文件 → 擴大搜尋範圍（自動調整 top_k）

### 5.3 二次 LLM 驗証（Self-RAG）
```
生成答案 → 幻覺檢測 LLM 驗証 → JSON 結果
{
  "is_grounded": true/false,
  "confidence_score": 0.0-1.0,
  "unsupported_claims": [...]
}
```

### 5.4 信心分數系統
| 分數 | 判決 | 行動 |
|------|------|------|
| ≥ 0.8 + 無未支持聲明 | ✅ PASS | 直接輸出 |
| 0.7 - 0.8 | ⚠️ UNCERTAIN | 輸出 + 警告 |
| < 0.7 或有未支持聲明 | ❌ FAIL | 重試（最多3次）→ 降級回應 |

### 5.5 強制來源引用
每個回應必須包含：文件名 + 分塊索引 + 相關度 + 摘要

---

## 🔍 六、自我驗証 & 自我 Debug 機制

### Self-RAG 流程
```
問題輸入
  ↓
向量搜尋（Top-K）
  ↓
相關性過濾（score > 0.3）
  ↓ 不夠相關？→ 擴大 top_k，重新搜尋
LLM 生成答案
  ↓
幻覺檢測（LLM as Judge）
  ↓ 失敗？→ 重試（最多3次）
通過 → 輸出 + 來源 + 信心分數
超限 → 降級回應（「無法找到可靠答案」）
```

### Debug 日誌（每步記錄）
```
[START] 問題: xxx
[嘗試 #1] top_k=5
[RETRIEVAL] 找到 5 個文件
[FILTER] 過濾後剩 3 個相關文件
[GENERATE] 模型: llama3.2, Token: 512
[VALIDATE] 判決=PASS, 信心=92%, 未支持聲明=[]
```

### 可透過 `/query?include_debug=true` 查看完整 Debug 日誌

---

## 🚀 七、快速開始（啟動步驟）

```bash
# 1. 建立虛擬環境
cd ai-rag-0
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/Mac

# 2. 安裝套件
pip install -r requirements.txt

# 3. 設定環境變數
copy .env.example .env
# 編輯 .env，填入 PostgreSQL 密碼 和 AI 供應商設定

# 4. 初始化數據庫
python scripts/init_db.py

# 5. 啟動 FastAPI 後端
uvicorn app.main:app --reload --port 8000

# 6. 啟動 Streamlit UI（另開終端）
streamlit run ui/streamlit_app.py --server.port 8501

# 7. 開啟瀏覽器
# API 文檔：http://localhost:8000/docs
# Web UI：http://localhost:8501
```

---

## 🔄 八、切換 AI 供應商（零代碼修改）

只需修改 `.env` 的一行：

```env
# 切換到 Gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=你的Key

# 切換回 Ollama
AI_PROVIDER=ollama

# 切換到 OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=你的Key
```

⚠️ **重要：切換 Embedding 模型時必須重新攝取所有文件！**
（因為向量維度不同，舊向量無效）

---

## ⚠️ 九、設計漏洞審查（Design Review）

### 🔴 高風險漏洞

| # | 漏洞 | 風險 | 解決方案 |
|---|------|------|---------|
| 1 | **Embedding 維度不一致** | 切換供應商後舊向量無法搜尋（維度 768 vs 1536 不匹配） | 在 documents 表加 `provider` 欄位，切換時清空並重新攝取；或為每個供應商建立獨立向量表 |
| 2 | **幻覺檢測用同一個 LLM** | 被驗証的 LLM 也是驗証者，可能「自圓其說」 | 使用獨立的 judge LLM，或用規則引擎（關鍵詞匹配）輔助驗証 |
| 3 | **無 API 認證** | 任何人可調用上傳/查詢 API，造成安全風險 | 加入 API Key 認證（`X-API-Key` Header）或 JWT |
| 4 | **Prompt Injection** | 用戶輸入惡意 Prompt 覆蓋系統指令 | 輸入清洗、長度限制（已做 max_length=1000）、敏感詞過濾 |

### 🟡 中風險漏洞

| # | 漏洞 | 風險 | 解決方案 |
|---|------|------|---------|
| 5 | **無速率限制** | API 被濫用或意外大量請求 | 加入 `slowapi` 速率限制（如 10次/分鐘/IP） |
| 6 | **重複文件上傳** | 同一文件多次上傳造成重複知識塊，影響準確性 | 上傳前用 source 名稱去重，或計算文件哈希值 |
| 7 | **大文件上傳無限制** | 超大文件導致記憶體溢出 | 加入文件大小限制（如 50MB），已有 tempfile 機制 |
| 8 | **無快取機制** | 相同問題重複全流程處理，效能浪費 | 加入 Redis 或記憶體快取，同一問題5分鐘內直接返回 |
| 9 | **並發搜尋競態** | 多用戶同時查詢可能爭用 DB Connection | 使用 SQLAlchemy Connection Pool（已設 pool_size=5） |

### 🟢 低風險 / 維護性問題

| # | 漏洞 | 風險 | 解決方案 |
|---|------|------|---------|
| 10 | **Anthropic 無 Embedding** | Anthropic 不提供 Embedding API，目前 fallback 到 Ollama | 文檔明確說明；或讓用戶額外設 `EMBED_PROVIDER` |
| 11 | **Chunk Overlap 計算** | Overlap 基於字符數而非 Token 數，可能超出 LLM Token 限制 | 加入 tiktoken 做 Token 計數，確保不超 Context Window |
| 12 | **pgvector IVFFlat 索引** | 文件少於 1000 時，IVFFlat 反而比全表掃描慢 | 文件數 > 1000 才建索引，小規模用 HNSW 或暴力搜尋 |
| 13 | **日誌無結構化存儲** | 日誌只存本地文件，難以大規模分析 | 生產環境改接 ELK 或 Grafana Loki |

---

## 📋 十、追加 Requirements（V2 新增）

```txt
# 安全 & 速率限制
slowapi==0.1.9          # API 速率限制
python-jose==3.3.0      # JWT 認證
passlib==1.7.4          # 密碼處理

# 快取
redis==5.0.8            # Redis 快取（可選）
cachetools==5.5.0       # 記憶體快取（已有）

# Token 計數（防超長 Chunk）
tiktoken==0.7.0         # OpenAI Token 計數器

# 文件哈希去重
hashlib                 # Python 內建

# 監控
prometheus-client==0.21.0
```

---

## 📊 十一、RAGAS 評估指標目標

| 指標 | 說明 | 目標 |
|------|------|------|
| **Faithfulness** | 答案是否忠於文件 | > 0.85 |
| **Answer Relevancy** | 答案是否切題 | > 0.80 |
| **Context Precision** | 檢索文件是否精準 | > 0.75 |
| **Context Recall** | 是否找到所有相關內容 | > 0.70 |

執行評估：
```bash
python scripts/evaluate_rag.py
```

---

## 📁 十二、項目文件結構

```
ai-rag-0/
├── RAG_PROJECT_PLAN_V2.md     # 本計劃書
├── requirements.txt            # Python 套件
├── .env.example               # 環境變數範例
├── .env                       # 實際環境變數（不提交 Git）
├── .gitignore
│
├── app/
│   ├── main.py                # FastAPI 入口
│   ├── config.py              # 多供應商設定
│   ├── database.py            # PostgreSQL + pgvector
│   │
│   ├── providers/             # AI 供應商（Strategy Pattern）
│   │   ├── base.py            # 抽象介面
│   │   ├── factory.py         # 工廠（根據設定選供應商）
│   │   ├── ollama_provider.py
│   │   ├── gemini_provider.py
│   │   └── openai_provider.py
│   │
│   ├── ingestion/             # 文件攝取
│   │   ├── loader.py          # 多格式文件載入
│   │   └── chunker.py         # 文字分塊
│   │
│   ├── retrieval/             # 向量檢索
│   │   └── vector_store.py    # pgvector 操作
│   │
│   ├── generation/            # 生成
│   │   ├── prompt.py          # Prompt 模板
│   │   └── chain.py           # RAG 鏈路 + 自我修正
│   │
│   ├── validation/            # 防幻覺驗証
│   │   └── hallucination_checker.py
│   │
│   └── api/                   # REST API
│       ├── health.py
│       ├── upload.py
│       └── query.py
│
├── ui/
│   └── streamlit_app.py       # Web UI
│
├── scripts/
│   ├── init_db.py             # 初始化數據庫
│   └── ingest_docs.py         # 批量攝取文件
│
├── tests/                     # 單元測試
│   └── ...
│
└── logs/                      # 日誌目錄
```

---

*由 Sally（超級軟件工程師）制定 ｜ ai-rag-0 v2.0*
