"""
app/ingestion/chunker.py — 文字分塊策略
Chunk 太大→檢索慢；太小→上下文不足
推薦：400-600 tokens，50 token 重疊
"""
from dataclasses import dataclass
from loguru import logger
from app.ingestion.loader import RawDocument
from app.config import get_settings

settings = get_settings()


@dataclass
class TextChunk:
    """分塊後的文字片段"""
    content: str
    source: str
    chunk_index: int
    metadata: dict


class TextChunker:
    """遞歸字符分塊器（推薦用於生產環境）"""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        # 分隔優先順序：段落 > 句子 > 詞 > 字符
        self.separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]

    def chunk_document(self, doc: RawDocument) -> list[TextChunk]:
        """將文件分成多個塊"""
        raw_chunks = self._recursive_split(doc.content)
        chunks = []
        for i, text in enumerate(raw_chunks):
            if text.strip():
                chunks.append(TextChunk(
                    content=text.strip(),
                    source=doc.source,
                    chunk_index=i,
                    metadata={**doc.metadata, "total_chunks": len(raw_chunks)},
                ))
        logger.debug(f"📦 [{doc.source}] 分成 {len(chunks)} 個 Chunk")
        return chunks

    def chunk_documents(self, docs: list[RawDocument]) -> list[TextChunk]:
        """批量分塊"""
        all_chunks = []
        for doc in docs:
            all_chunks.extend(self.chunk_document(doc))
        logger.info(f"📦 共生成 {len(all_chunks)} 個 Chunk")
        return all_chunks

    def _recursive_split(self, text: str, separators: list[str] = None) -> list[str]:
        """遞歸分塊：優先用段落分，太大再細分"""
        if separators is None:
            separators = self.separators

        final_chunks = []
        separator = separators[-1]

        # 找到合適的分隔符
        for sep in separators:
            if sep in text:
                separator = sep
                break

        splits = text.split(separator) if separator else list(text)

        current_chunk = ""
        for split in splits:
            if len(current_chunk) + len(split) + len(separator) <= self.chunk_size:
                current_chunk += (separator if current_chunk else "") + split
            else:
                if current_chunk:
                    final_chunks.append(current_chunk)
                # 如果單個分割已超過 chunk_size，遞歸細分
                if len(split) > self.chunk_size and len(separators) > 1:
                    sub_chunks = self._recursive_split(split, separators[1:])
                    final_chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] if sub_chunks else split
                else:
                    current_chunk = split

        if current_chunk:
            final_chunks.append(current_chunk)

        # 加入重疊（Overlap）確保上下文連貫
        return self._add_overlap(final_chunks)

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        """在相鄰 Chunk 間加入重疊內容，保留上下文"""
        if self.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            overlap = chunks[i - 1][-self.chunk_overlap:]
            result.append(overlap + chunks[i])
        return result
