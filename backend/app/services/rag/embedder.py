"""
智慧学伴 RAG 嵌入模块
文本分块(512token/50overlap) + 批量嵌入(OpenAI Embedding API)
"""
import logging
from typing import List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# 分块参数
CHUNK_SIZE = 512  # token 数
CHUNK_OVERLAP = 50  # 重叠 token 数
APPROX_CHARS_PER_TOKEN = 1.5  # 中英文混合估算


class Embedder:
    """文本嵌入器"""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_base = settings.OPENAI_API_BASE
        self.model = "text-embedding-3-small"

    def chunk_text(
        self,
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> List[str]:
        """
        文本分块

        Args:
            text: 原始文本
            chunk_size: 每块大小（近似token数）
            overlap: 重叠大小

        Returns:
            分块列表
        """
        if not text or not text.strip():
            return []

        # 简化分块：按字符数近似token数
        chars_per_chunk = int(chunk_size * APPROX_CHARS_PER_TOKEN)
        chars_overlap = int(overlap * APPROX_CHARS_PER_TOKEN)

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chars_per_chunk
            chunk = text[start:end]

            # 尝试在句子边界切分
            if end < text_len:
                # 向前查找最近的句号/换行
                for sep in ["。", ".", "！", "！", "\n", "；", ";"]:
                    last_sep = chunk.rfind(sep)
                    if last_sep > chars_per_chunk // 2:
                        chunk = chunk[: last_sep + 1]
                        end = start + last_sep + 1
                        break

            chunks.append(chunk.strip())
            start = end - chars_overlap

        # 过滤空块
        return [c for c in chunks if c]

    async def embed_query(self, text: str) -> List[float]:
        """
        嵌入单条查询文本

        Args:
            text: 查询文本

        Returns:
            嵌入向量
        """
        embeddings = await self._call_embedding_api([text])
        return embeddings[0] if embeddings else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量嵌入文本

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        if not texts:
            return []

        # 分批调用（每批最多 100 条）
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await self._call_embedding_api(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """
        调用 OpenAI Embedding API

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        if not self.api_key:
            logger.warning("OPENAI_API_KEY 未配置，使用零向量")
            return [[0.0] * 1536 for _ in texts]

        url = f"{self.api_base}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings
        except Exception as e:
            logger.error(f"Embedding API 调用失败: {e}")
            # 回退零向量
            return [[0.0] * 1536 for _ in texts]
