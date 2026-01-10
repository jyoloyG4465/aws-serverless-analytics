"""
RAGクライアント - S3ベクトル検索

処理フロー:
1. S3からベクトルデータ読み込み
2. クエリをベクトル化
3. コサイン類似度で類似データ取得
"""

import json
import math
import boto3
from typing import List, Dict, Any, Optional

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name="ap-northeast-1")

EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v1"
EMBEDDING_DIMENSION = 1536


class RAGClient:
    """S3ベクトル検索クライアント"""

    def __init__(self, vectors_bucket: str, region: str = "ap-northeast-1"):
        self.vectors_bucket = vectors_bucket
        self.bedrock = boto3.client("bedrock-runtime", region_name=region)
        self._cache: Dict[str, dict] = {}

    def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        クエリに関連するデータを検索

        Args:
            query: 検索クエリ（自然言語）
            user_id: ユーザーID
            top_k: 返す件数

        Returns:
            関連データのリスト（類似度順）
        """
        # ベクトルデータ読み込み
        vectors_data = self._load_vectors(user_id)
        if not vectors_data or vectors_data.get("count", 0) == 0:
            print(f"No vectors found for user {user_id}")
            return []

        # クエリをベクトル化
        query_vector = self._get_embedding(query)

        # コサイン類似度で検索
        results = self._similarity_search(
            query_vector,
            vectors_data["vectors"],
            vectors_data["texts"],
            vectors_data["metadata"],
            top_k
        )

        return results

    def _load_vectors(self, user_id: str) -> Optional[dict]:
        """S3からベクトルデータを読み込み（キャッシュあり）"""
        cache_key = f"vectors_{user_id}"

        if cache_key in self._cache:
            print(f"Using cached vectors for user {user_id}")
            return self._cache[cache_key]

        key = f"vectors/{user_id}/embeddings.json"

        try:
            response = s3.get_object(Bucket=self.vectors_bucket, Key=key)
            data = json.loads(response["Body"].read().decode("utf-8"))
            self._cache[cache_key] = data
            print(f"Loaded {data.get('count', 0)} vectors for user {user_id}")
            return data

        except s3.exceptions.NoSuchKey:
            print(f"Vectors not found: s3://{self.vectors_bucket}/{key}")
            return None
        except Exception as e:
            print(f"Error loading vectors: {str(e)}")
            return None

    def _get_embedding(self, text: str) -> List[float]:
        """テキストをベクトル化"""
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIMENSION

        text = text[:8000]  # Titan制限

        try:
            response = self.bedrock.invoke_model(
                modelId=EMBEDDING_MODEL_ID,
                body=json.dumps({"inputText": text})
            )
            result = json.loads(response["body"].read())
            return result["embedding"]

        except Exception as e:
            print(f"Embedding error: {str(e)}")
            return [0.0] * EMBEDDING_DIMENSION

    def _similarity_search(
        self,
        query_vector: List[float],
        vectors: List[List[float]],
        texts: List[str],
        metadata: List[dict],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """コサイン類似度で検索"""
        scores = []

        for i, vec in enumerate(vectors):
            similarity = self._cosine_similarity(query_vector, vec)
            scores.append((i, similarity))

        # 類似度でソート
        scores.sort(key=lambda x: x[1], reverse=True)

        # 上位k件を返す
        results = []
        for i, (idx, score) in enumerate(scores[:top_k]):
            results.append({
                "rank": i + 1,
                "score": round(score, 4),
                "text": texts[idx],
                "metadata": metadata[idx]
            })

        return results

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """コサイン類似度を計算"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


def format_rag_results(results: List[Dict[str, Any]]) -> str:
    """RAG結果をBedrockに渡すテキスト形式に変換"""
    if not results:
        return "関連するデータが見つかりませんでした。"

    lines = [f"関連する視聴履歴 {len(results)}件:"]

    for r in results:
        meta = r["metadata"]
        lines.append(
            f"- {meta.get('title', '不明')} "
            f"(チャンネル: {meta.get('channel_name', '不明')}, "
            f"視聴日: {meta.get('watched_at', '不明')[:10]})"
        )

    return "\n".join(lines)
