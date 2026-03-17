# 🤖 ai-rag-0

> **RAG（檢索增強生成）內部知識庫搜尋系統**  
> 支援多AI供應商 · PostgreSQL 向量存儲 · 內建防幻覺機制

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue?logo=postgresql)](https://postgresql.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-red?logo=streamlit)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📌 項目簡介

**ai-rag-0** 係一個企業級 RAG（Retrieval-Augmented Generation）知識庫系統。

用戶上傳內部文件（PDF、Word、CSV 等），系統將文件向量化存入 PostgreSQL，用戶提問時自動檢索最相關的文件片段，再交由 AI 生成準確、有來源依據的答案。

### 核心特色

| 功能 | 說明 |
|------|------|
| 🔌 **多AI供應商** | Ollama（本地）/ Gemini / OpenAI — 改一行設定即可切換 |
| 🛡️ **防幻覺機制** | Prompt 限制 + 相似度過濾 + LLM 二次驗証 + 信心分數 |
| 🔄 **自我修正** | Self-RAG 循環，最多3次自動重試直至通過驗証 |
| 📎 **強制引用** | 每個答案必須附上文件來源和摘要，不可憑空回答 |
| 📚 **混合文件** | PDF / Word / CSV / Excel / TXT / HTML / PPT |
| 🗄️ **pgvector** | PostgreSQL 原生向量搜尋，企業級穩定性 |
| 🔍 **Debug模式** | 透過 API 查看完整 RAG 處理步驟日誌 |

---

## 🏗️ 系統架構

```
用戶 (Streamlit UI)
      │
      ▼
FastAPI 後端
  ├── POST /upload → 文件載入 → 分塊 → 向量化 → PostgreSQL
  └── POST /query  → 向量搜尋 → Prompt組裝 → LLM生成
                                                    │
                                             幻覺檢測驗証
                                             信心 < 0.7 → 重試
                                             信心 ≥ 0.8 → 輸出
                                                    │
                                         答案 + 來源 + 信心分數
```

---

## ✅ 前提條件

### 必裝軟件

```bash
# 1. Python 3.11+
python --version   # 確認版本

# 2. PostgreSQL 15+（需啟用 pgvector 擴充）
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. Ollama（如使用本地 AI）
# 下載：https://ollama.ai/download
ollama pull nomic-embed-text    # Embedding 模型（必須）
ollama pull llama3.2            # LLM 模型
```

### AI 供應商選擇

只需在 `.env` 設定其中一個：

| 供應商 | 需要 | 費用 |
|--------|------|------|
| **Ollama**（推薦入門） | 本地安裝 | 免費，完全私隱 |
| **Google Gemini** | `GEMINI_API_KEY` | 有免費額度 |
| **OpenAI** | `OPENAI_API_KEY` | 按用量收費 |

---

## 🚀 快速開始

### 1. Clone 項目

```bash
git clone https://github.com/SpaceMichael/ai-rag-0.git
cd ai-rag-0
```

### 2. 建立虛擬環境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / Mac
python -m venv venv
source venv/bin/activate
```

### 3. 安裝套件

```bash
pip install -r requirements.txt
```

### 4. 設定環境變數

```bash
# Windows
copy .env.example .env

# Linux / Mac
cp .env.example .env
```

編輯 `.env`，填入必要設定：

```env
# 選擇 AI 供應商
AI_PROVIDER=ollama          # 或 gemini / openai

# PostgreSQL 連接
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_rag_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=你的密碼
DATABASE_URL=postgresql://postgres:你的密碼@localhost:5432/ai_rag_db

# 如用 Gemini（可選）
# GEMINI_API_KEY=AIzaSyxxxx

# 如用 OpenAI（可選）
# OPENAI_API_KEY=sk-xxxx
```

### 5. 初始化數據庫

```bash
python scripts/init_db.py
```

### 6. 啟動服務

```bash
# 終端 1：啟動 FastAPI 後端
uvicorn app.main:app --reload --port 8000

# 終端 2：啟動 Streamlit UI
streamlit run ui/streamlit_app.py --server.port 8501
```

### 7. 開啟瀏覽器

| 服務 | 網址 |
|------|------|
| 🌐 Web UI | http://localhost:8501 |
| 📖 API 文檔 | http://localhost:8000/docs |
| ❤️ 健康檢查 | http://localhost:8000/api/v1/health |

---

## 🔄 切換 AI 供應商

**只需修改 `.env` 一行，無需改任何代碼：**

```env
# 切換到 Gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=你的Key
GEMINI_EMBED_MODEL=models/embedding-001

# 切換到 OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=你的Key
EMBED_DIMENSIONS=1536       # OpenAI embedding 維度不同！

# 切回本地 Ollama
AI_PROVIDER=ollama
```

> ⚠️ **重要：** 切換 Embedding 供應商後，必須清空並重新上傳所有文件（向量維度不同，舊向量無效）

---

## 📡 API 使用

### 上傳文件

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@你的文件.pdf"
```

### 提問查詢

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "你的問題", "top_k": 5, "include_debug": false}'
```

**回應格式：**
```json
{
  "answer": "根據文件...",
  "sources": [
    {
      "file": "policy.pdf",
      "chunk_index": 3,
      "similarity": 0.923,
      "excerpt": "..."
    }
  ],
  "confidence_score": 0.92,
  "verdict": "PASS",
  "warning": "",
  "attempt_count": 1,
  "elapsed_ms": 1234.5,
  "provider": "ollama"
}
```

### 查看知識庫狀態

```bash
curl http://localhost:8000/api/v1/sources
```

---

## 📁 項目結構

```
ai-rag-0/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 多供應商設定管理
│   ├── database.py                # PostgreSQL + pgvector
│   ├── providers/                 # AI 供應商（Strategy Pattern）
│   │   ├── base.py                # 抽象介面
│   │   ├── factory.py             # 工廠（根據設定選供應商）
│   │   ├── ollama_provider.py     # Ollama 本地 AI
│   │   ├── gemini_provider.py     # Google Gemini
│   │   └── openai_provider.py     # OpenAI
│   ├── ingestion/                 # 文件攝取
│   │   ├── loader.py              # 多格式載入器
│   │   └── chunker.py             # 遞歸文字分塊
│   ├── retrieval/
│   │   └── vector_store.py        # pgvector 向量操作
│   ├── generation/
│   │   ├── prompt.py              # Prompt 模板（防幻覺）
│   │   └── chain.py               # RAG 鏈路 + 自我修正
│   ├── validation/
│   │   └── hallucination_checker.py  # 幻覺檢測器
│   └── api/
│       ├── health.py              # 健康檢查
│       ├── upload.py              # 文件上傳
│       └── query.py               # 問答查詢
├── ui/
│   └── streamlit_app.py           # Streamlit Web UI
├── scripts/
│   └── init_db.py                 # 數據庫初始化
├── tests/                         # 測試（待補充）
├── requirements.txt
├── .env.example                   # 環境變數範例
├── .gitignore
└── RAG_PROJECT_PLAN_V2.md         # 完整設計計劃書
```

---

## 🛡️ 防幻覺機制詳解

### 信心分數系統

| 分數 | 判決 | 行動 |
|------|------|------|
| ≥ 0.8，無未支持聲明 | ✅ PASS | 直接輸出答案 + 來源 |
| 0.7 – 0.8 | ⚠️ UNCERTAIN | 輸出 + 警告提示 |
| < 0.7 或有幻覺聲明 | ❌ FAIL | 自動重試（最多3次） |
| 超過最大重試 | 🚫 降級 | 回應「找不到可靠答案」 |

### Self-RAG 流程

```
問題 → 向量搜尋 → 相關性過濾 → LLM生成
                                    ↓
                             幻覺檢測 (LLM as Judge)
                                    ↓
                         PASS → 輸出答案 + 來源
                         FAIL → 擴大搜尋 → 重試
                        超限  → 安全降級回應
```

---

## ⚠️ 已知限制

1. **切換 Embedding 模型**需重新攝取所有文件（維度不同）
2. **幻覺檢測**使用同一 LLM，生產環境建議用獨立 Judge 模型
3. 目前無 **API 認證**，建議生產環境加入 API Key 或 JWT
4. **Anthropic Claude** 無官方 Embedding API，需搭配 Ollama Embedding 使用

詳見 [RAG_PROJECT_PLAN_V2.md](RAG_PROJECT_PLAN_V2.md) 設計漏洞審查章節。

---

## 🗺️ 開發路線圖

- [x] 多AI供應商架構（Strategy Pattern）
- [x] PostgreSQL + pgvector 向量存儲
- [x] 混合文件類型支援
- [x] 防幻覺機制 + Self-RAG 自我修正
- [x] FastAPI REST API + Streamlit UI
- [ ] API Key 認證
- [ ] Redis 快取
- [ ] Anthropic Claude 供應商
- [ ] RAGAS 自動評估
- [ ] Docker Compose 一鍵部署

---

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request！

---

## 📄 License

MIT License — 自由使用、修改、分發

---

## 🔁 下次繼續開發（重要！請勿刪除此節）

> 如果你關閉了 Copilot / AI 助手，重新開始時請跟以下步驟操作。

### Step 1 — 告訴 AI 助手讀取項目

複製以下提示語，貼到新的 Copilot / AI 對話框：

```
請閱讀 https://github.com/SpaceMichael/ai-rag-0 的 README.md 和
RAG_PROJECT_PLAN_V2.md，然後繼續開發這個項目。
我叫你做 Sally（超級軟件工程師），請用中文回應我。
```

### Step 2 — 拉最新代碼

```bash
git clone https://github.com/SpaceMichael/ai-rag-0.git
cd ai-rag-0
# 或如已有本地版本：
git pull origin master
```

### Step 3 — 建立 Python 環境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / Mac
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Step 4 — 設定環境變數

```bash
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac
```

編輯 `.env`，最少要填：
```env
AI_PROVIDER=ollama          # 或 gemini / openai
POSTGRES_PASSWORD=你的密碼
DATABASE_URL=postgresql://postgres:你的密碼@localhost:5432/ai_rag_db
```

### Step 5 — 準備外部服務

```bash
# PostgreSQL：建立數據庫 + 啟用 pgvector
psql -U postgres -c "CREATE DATABASE ai_rag_db;"
psql -U postgres -d ai_rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Ollama（如用本地 AI）：下載模型
ollama pull nomic-embed-text
ollama pull llama3.2
```

### Step 6 — 初始化數據庫並啟動

```bash
# 初始化數據庫表
python scripts/init_db.py

# 終端 1：啟動後端 API
uvicorn app.main:app --reload --port 8000

# 終端 2：啟動前端 UI
streamlit run ui/streamlit_app.py --server.port 8501
```

### Step 7 — 重新上傳知識庫文件

> ⚠️ 向量數據存在 PostgreSQL，不在 Git 裡。每次在新機器部署後，需要重新上傳文件。

打開 http://localhost:8501，在左側欄上傳你的 PDF / Word / CSV 等文件。

### 📌 項目現有 Roadmap（下次繼續的方向）

詳見 [RAG_PROJECT_PLAN_V2.md](RAG_PROJECT_PLAN_V2.md) 第九節「設計漏洞審查」。

待辦事項（優先順序）：
- [ ] 加入 API Key 認證（防止未授權訪問）
- [ ] 加入文件哈希去重（防止重複上傳）
- [ ] Redis 快取（相同問題直接返回）
- [ ] RAGAS 自動評估腳本
- [ ] Docker Compose 一鍵部署
- [ ] Anthropic Claude 完整 Embedding 支援（目前 fallback Ollama）
