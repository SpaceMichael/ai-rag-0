"""
app/validation/hallucination_checker.py — 幻覺檢測器
核心防幻覺機制：用 LLM 驗証 LLM 的輸出
"""
import json
import re
from dataclasses import dataclass
from loguru import logger
from app.providers.base import BaseAIProvider
from app.generation.prompt import HALLUCINATION_CHECK_PROMPT
from app.config import get_settings

settings = get_settings()


@dataclass
class ValidationResult:
    """驗証結果"""
    is_grounded: bool          # 答案是否完全基於文件
    confidence_score: float    # 信心分數 0.0-1.0
    supported_claims: list     # 有文件支持的聲明
    unsupported_claims: list   # 無文件支持的聲明（潛在幻覺）
    verdict: str               # PASS / FAIL / UNCERTAIN
    warning_message: str = ""  # 警告訊息（給用戶看）


class HallucinationChecker:
    """
    幻覺檢測器
    策略：用同一個（或獨立的）LLM 作為「裁判」，
    驗証答案中每個聲明是否有文件根據
    """

    def __init__(self, provider: BaseAIProvider):
        self.provider = provider
        self.threshold = settings.hallucination_threshold
        self.min_confidence = settings.min_confidence_score

    def check(self, answer: str, context_docs: list[dict]) -> ValidationResult:
        """
        執行幻覺檢測
        :param answer: LLM 生成的答案
        :param context_docs: 用於生成答案的文件列表
        :return: ValidationResult
        """
        if not context_docs:
            return ValidationResult(
                is_grounded=False,
                confidence_score=0.0,
                supported_claims=[],
                unsupported_claims=["無參考文件"],
                verdict="FAIL",
                warning_message="⚠️ 知識庫中無相關文件，答案不可靠",
            )

        context_text = "\n---\n".join(doc["content"] for doc in context_docs)
        prompt = HALLUCINATION_CHECK_PROMPT.format(
            context=context_text,
            answer=answer,
        )

        try:
            response = self.provider.generate(prompt=prompt)
            result = self._parse_validation_response(response.content)
            result.warning_message = self._build_warning(result)
            return result

        except Exception as e:
            logger.error(f"❌ 幻覺檢測失敗: {e}")
            # 失敗時傳回保守結果
            return ValidationResult(
                is_grounded=False,
                confidence_score=0.0,
                supported_claims=[],
                unsupported_claims=[],
                verdict="UNCERTAIN",
                warning_message="⚠️ 無法完成驗証，請人工確認答案準確性",
            )

    def _parse_validation_response(self, response_text: str) -> ValidationResult:
        """解析 LLM 返回的 JSON 驗証結果"""
        try:
            # 提取 JSON（處理 LLM 可能在 JSON 前後加文字的情況）
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if not json_match:
                raise ValueError("回應中找不到 JSON")

            data = json.loads(json_match.group())
            score = float(data.get("confidence_score", 0.5))
            is_grounded = data.get("is_grounded", False)
            unsupported = data.get("unsupported_claims", [])

            # 最終判決
            if is_grounded and score >= self.threshold and not unsupported:
                verdict = "PASS"
            elif score < self.min_confidence or (not is_grounded and unsupported):
                verdict = "FAIL"
            else:
                verdict = "UNCERTAIN"

            return ValidationResult(
                is_grounded=is_grounded,
                confidence_score=score,
                supported_claims=data.get("supported_claims", []),
                unsupported_claims=unsupported,
                verdict=verdict,
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"⚠️ 解析驗証回應失敗: {e}，回應內容: {response_text[:200]}")
            return ValidationResult(
                is_grounded=False,
                confidence_score=0.5,
                supported_claims=[],
                unsupported_claims=[],
                verdict="UNCERTAIN",
            )

    def _build_warning(self, result: ValidationResult) -> str:
        """根據驗証結果建立用戶警告訊息"""
        if result.verdict == "PASS":
            return ""
        if result.verdict == "FAIL":
            claims = "、".join(result.unsupported_claims[:3])
            return f"⚠️ 答案中部分內容可能無文件支持：{claims}。建議人工核實。"
        return "⚠️ 答案置信度較低，請謹慎參考，建議人工確認。"
