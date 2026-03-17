"""
app/generation/prompt.py — Prompt 模板設計
核心防幻覺策略：強制 LLM 只根據文件內容回答
"""

# =============================================
# 主問答 Prompt（強制基於文件）
# =============================================
RAG_SYSTEM_PROMPT = """你係一個嚴謹、可靠的知識庫助手。

【核心規則 - 必須遵守】
1. 只根據以下提供的【參考文件】內容回答問題
2. 如果參考文件中找不到答案，必須回答：「根據現有知識庫文件，未能找到相關資訊，建議查閱其他來源或諮詢相關人員。」
3. 回答必須包含具體來源引用（文件名稱）
4. 絕對不要憑空編造、猜測或補充文件以外的資訊
5. 如果問題含糊，先說明你的理解，再回答

【回答格式】
- 先直接回答問題
- 然後列出引用來源
- 如有不確定之處，明確說明

你的回答要準確、簡潔、有用。"""


def build_rag_prompt(question: str, context_docs: list[dict]) -> str:
    """
    組裝 RAG 提問 Prompt
    :param question: 用戶問題
    :param context_docs: 從向量庫取得的相關文件列表
    :return: 完整 Prompt 字串
    """
    if not context_docs:
        return f"【問題】{question}\n\n【注意】知識庫中未找到相關文件，請說明無法回答的原因。"

    context_parts = []
    for i, doc in enumerate(context_docs, 1):
        score = doc.get("similarity_score", 0)
        context_parts.append(
            f"【文件 {i}】來源：{doc['source']} | 相關度：{score:.2%}\n"
            f"{doc['content']}"
        )

    context_str = "\n\n---\n\n".join(context_parts)

    return f"""【參考文件】
{context_str}

---

【問題】
{question}

請根據以上參考文件回答問題，並在回答末尾列出引用的文件來源。"""


# =============================================
# 幻覺驗証 Prompt
# =============================================
HALLUCINATION_CHECK_PROMPT = """你係一個嚴格的事實核查員。

你的任務：
驗証以下【答案】中的每個聲明是否有【參考文件】的直接支持。

【參考文件】
{context}

【待驗証答案】
{answer}

請以 JSON 格式回應（只返回 JSON，不要其他文字）：
{{
  "is_grounded": true 或 false,
  "confidence_score": 0.0 到 1.0 的數值,
  "supported_claims": ["有文件支持的聲明列表"],
  "unsupported_claims": ["無文件支持、可能是幻覺的聲明列表"],
  "verdict": "PASS 或 FAIL"
}}"""


# =============================================
# 相關性評分 Prompt
# =============================================
RELEVANCE_CHECK_PROMPT = """評估以下文件片段是否與問題相關。

【問題】{question}

【文件片段】{chunk}

只返回 JSON：
{{"is_relevant": true 或 false, "relevance_score": 0.0 到 1.0}}"""
