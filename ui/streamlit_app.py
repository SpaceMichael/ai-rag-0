"""
ui/streamlit_app.py — Streamlit Web UI
簡潔問答介面，顯示答案、來源、信心分數
"""
import streamlit as st
import requests
import json

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(
    page_title="ai-rag-0 知識庫",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 ai-rag-0 內部知識庫")
st.caption("RAG 系統 | 防幻覺 | 本地 AI")

# ─── 側邊欄：上傳文件 ────────────────────────────
with st.sidebar:
    st.header("📚 管理知識庫")

    uploaded_file = st.file_uploader(
        "上傳文件",
        type=["pdf", "docx", "txt", "csv", "xlsx", "html", "pptx"],
        help="支援 PDF, Word, TXT, CSV, Excel, HTML, PPT",
    )
    if uploaded_file and st.button("📤 上傳到知識庫"):
        with st.spinner("處理中..."):
            resp = requests.post(
                f"{API_BASE}/upload",
                files={"file": (uploaded_file.name, uploaded_file.getvalue())},
            )
        if resp.status_code == 200:
            data = resp.json()
            st.success(f"✅ {data['message']}")
        else:
            st.error(f"❌ 上傳失敗: {resp.text}")

    st.divider()
    st.subheader("📊 知識庫狀態")
    if st.button("🔄 更新統計"):
        resp = requests.get(f"{API_BASE}/sources")
        if resp.status_code == 200:
            stats = resp.json()
            st.metric("文件數", stats["total_sources"])
            st.metric("知識塊數", stats["total_chunks"])
            if stats["sources"]:
                st.write("**已上傳文件：**")
                for src in stats["sources"]:
                    st.text(f"• {src}")

    st.divider()
    show_debug = st.checkbox("🔍 顯示 Debug 日誌", value=False)
    st.caption("Debug 模式顯示 RAG 內部處理過程")

# ─── 主界面：問答 ────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("輸入你的問題..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("🔍 搜尋知識庫並生成答案..."):
            resp = requests.post(
                f"{API_BASE}/query",
                json={"question": question, "include_debug": show_debug},
            )

        if resp.status_code != 200:
            st.error(f"❌ API 錯誤: {resp.text}")
        else:
            data = resp.json()

            # 信心分數徽章
            score = data["confidence_score"]
            verdict = data["verdict"]
            color = "green" if verdict == "PASS" else ("orange" if verdict == "UNCERTAIN" else "red")
            st.markdown(
                f"**信心分數：** :{color}[{'✅' if verdict == 'PASS' else '⚠️'} {score:.0%} ({verdict})]"
            )

            # 警告訊息
            if data.get("warning"):
                st.warning(data["warning"])

            # 答案
            st.markdown(data["answer"])

            # 來源引用
            if data.get("sources"):
                with st.expander(f"📎 引用來源 ({len(data['sources'])} 個)"):
                    for i, src in enumerate(data["sources"], 1):
                        st.markdown(
                            f"**[{i}] {src['file']}** "
                            f"（相關度: {src['similarity']:.2%}）\n\n"
                            f"> {src.get('excerpt', '')}"
                        )

            # 效能資訊
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            meta_col1.caption(f"⏱️ {data['elapsed_ms']:.0f}ms")
            meta_col2.caption(f"🔌 {data['provider']}")
            meta_col3.caption(f"🔄 嘗試 {data['attempt_count']} 次")

            # Debug 日誌
            if show_debug and data.get("debug_log"):
                with st.expander("🔍 Debug 日誌"):
                    for log in data["debug_log"]:
                        st.code(log, language=None)

            st.session_state.messages.append({"role": "assistant", "content": data["answer"]})
